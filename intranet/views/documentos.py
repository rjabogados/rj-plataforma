import io
import hashlib
import mimetypes
import os
from urllib.parse import quote
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.files.base import ContentFile
from django.http import FileResponse, Http404
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PyPDF2 import PdfReader, PdfWriter

# Importamos los modelos y el motor de automatización de Word/PDF
from intranet.models import CategoriaDocumento, PlantillaDocumento, DocumentoGenerado, FirmaDigital, Colaborador
from intranet.servicios.motor_documentos import generar_documento_para_colaborador
from .utils import solo_directivos, obtener_ip_cliente, filtrar_colaboradores, filtros_personal_disponibles

MAX_TEMPLATE_SIZE = 10 * 1024 * 1024


def es_docx_valido(archivo):
    extension = os.path.splitext(archivo.name)[1].lower()
    return extension == '.docx' and archivo.size <= MAX_TEMPLATE_SIZE


def build_inline_file_response(field_file):
    if not field_file or not field_file.name:
        raise Http404("Archivo no disponible")

    storage = field_file.storage
    if not storage.exists(field_file.name):
        raise Http404("Archivo no disponible")

    filename = os.path.basename(field_file.name)
    content_type, _ = mimetypes.guess_type(filename)
    response = FileResponse(storage.open(field_file.name, 'rb'), content_type=content_type or 'application/octet-stream')
    response['Content-Disposition'] = f"inline; filename*=UTF-8''{quote(filename)}"
    return response

@login_required(login_url='login')
@solo_directivos
def documentos_admin(request):
    """Panel de despacho para generar contratos y reportes basados en plantillas."""
    plantillas = PlantillaDocumento.objects.filter(activo=True)
    perfil_actual = getattr(request.user, 'perfil', None)
    colaboradores = filtrar_colaboradores(
        Colaborador.objects.select_related('user', 'area', 'cargo', 'negocio'),
        request.GET,
        perfil_actual,
    )

    if request.method == 'POST':
        plantilla_id = request.POST.get('plantilla_id')
        colaborador_id = request.POST.get('colaborador_id')

        if plantilla_id and colaborador_id:
            plantilla = get_object_or_404(PlantillaDocumento, id=plantilla_id)
            colaborador = get_object_or_404(User, id=colaborador_id)
            nuevo_doc = generar_documento_para_colaborador(plantilla, colaborador)

            if nuevo_doc:
                messages.success(request, f"¡Éxito! Documento '{plantilla.nombre}' generado para {colaborador.first_name}.")
            else:
                messages.error(request, "Error crítico al convertir a PDF. Revisa el Word original.")
            return redirect('documentos_admin')

    historial = DocumentoGenerado.objects.all().order_by('-fecha_emision')[:15]
    return render(request, 'intranet/documentos/despachar_documentos.html', {
        'plantillas': plantillas,
        'colaboradores': colaboradores,
        'historial': historial,
        'negocios': Colaborador._meta.get_field('negocio').remote_field.model.objects.all(),
        'areas': Colaborador._meta.get_field('area').remote_field.model.objects.filter(activa=True).order_by('nombre'),
        'cargos': Colaborador._meta.get_field('cargo').remote_field.model.objects.filter(activa=True).select_related('area').order_by('nombre'),
        'filtros_disponibles': filtros_personal_disponibles(perfil_actual),
    })

@login_required(login_url='login')
@solo_directivos
def gestionar_plantillas(request):
    """Biblioteca digital para subir nuevos formatos .docx con tags {{ variables }}."""
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        categoria_id = request.POST.get('categoria_id')
        archivo = request.FILES.get('archivo_word')
        
        if nombre and archivo:
            if not es_docx_valido(archivo):
                messages.error(request, "La plantilla debe ser un archivo .docx de hasta 10 MB.")
                return redirect('gestionar_plantillas')
            categoria = CategoriaDocumento.objects.filter(id=categoria_id).first()
            PlantillaDocumento.objects.create(nombre=nombre, categoria=categoria, archivo_word=archivo, activo=True)
            messages.success(request, "¡Excelente! La plantilla se ha guardado correctamente en el sistema.")
            return redirect('gestionar_plantillas')
        else:
            messages.error(request, "Hubo un problema. Asegúrate de rellenar el nombre y adjuntar el Word.")

    plantillas = PlantillaDocumento.objects.all().order_by('-fecha_creacion')
    categorias = CategoriaDocumento.objects.all()
    return render(request, 'intranet/documentos/gestionar_plantillas.html', {'plantillas': plantillas, 'categorias': categorias})

@login_required(login_url='login')
def documentos_personal(request):
    """Bóveda del trabajador para ver y descargar sus documentos/boletas."""
    mis_docs = DocumentoGenerado.objects.filter(colaborador=request.user).order_by('-fecha_emision')
    return render(request, 'intranet/documentos/documentos_personal.html', {'documentos': mis_docs})


@login_required(login_url='login')
def ver_documento_personal(request, doc_id):
    documento = get_object_or_404(DocumentoGenerado, id=doc_id, colaborador=request.user)
    return build_inline_file_response(documento.archivo_pdf)


@login_required(login_url='login')
@solo_directivos
def ver_documento_admin(request, doc_id):
    documento = get_object_or_404(DocumentoGenerado, id=doc_id)
    return build_inline_file_response(documento.archivo_pdf)

@login_required(login_url='login')
def firmar_documento(request, doc_id):
    """Motor forense de Firma Digital. Acopla una hoja de certificación legal inalterable."""
    documento = get_object_or_404(DocumentoGenerado, id=doc_id, colaborador=request.user)

    if request.method == 'POST' and documento.estado == 'PENDIENTE':
        acepto_terminos = request.POST.get('acepto_terminos') == 'on'
        if not acepto_terminos:
            return redirect('firmar_documento', doc_id=doc_id)

        try:
            ip_cliente = obtener_ip_cliente(request)
            fecha_actual = timezone.now()
            fecha_str = fecha_actual.strftime("%d/%m/%Y a las %H:%M:%S")
            
            # --- 1. CREAMOS LA HOJA DE AUDITORÍA (CERTIFICADO) ---
            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=letter)
            
            can.setFont("Helvetica-Bold", 16)
            can.drawString(50, 700, "CERTIFICADO DE FIRMA ELECTRÓNICA")
            can.setFont("Helvetica-Bold", 12)
            can.drawString(50, 680, "RJ Abogados - Plataforma Talent")
            
            can.setFont("Helvetica", 11)
            can.drawString(50, 640, "Documento firmado digitalmente por:")
            can.setFont("Helvetica-Bold", 11)
            can.drawString(50, 620, f"Nombre: {request.user.first_name} {request.user.last_name}")
            can.drawString(50, 600, f"DNI / Identificación: {request.user.username}")
            
            can.setFont("Helvetica", 11)
            can.drawString(50, 560, "Rastro Forense de Seguridad:")
            can.drawString(50, 540, f"Fecha y Hora Exacta: {fecha_str}")
            can.drawString(50, 520, f"Dirección IP de Origen: {ip_cliente}")
            
            can.setFont("Helvetica-Oblique", 9)
            can.drawString(50, 480, "Este anexo garantiza la validez legal y autoría del documento adjunto.")
            can.drawString(50, 465, "Cualquier alteración posterior al archivo invalidará la firma criptográfica.")
            
            can.save()
            packet.seek(0)
            pdf_certificado = PdfReader(packet)

            # --- 2. ENGRAPAMOS EL CERTIFICADO AL DOCUMENTO ORIGINAL ---
            pdf_original = PdfReader(documento.archivo_pdf.path)
            writer = PdfWriter()

            for page in pdf_original.pages: 
                writer.add_page(page)
            writer.add_page(pdf_certificado.pages[0])

            output_pdf = io.BytesIO()
            writer.write(output_pdf)
            output_pdf.seek(0)

            # --- 3. CALCULAMOS EL HASH FINAL DE SEGURIDAD ---
            sha256_hash = hashlib.sha256(output_pdf.read()).hexdigest()
            output_pdf.seek(0)

            # --- 4. SOBREESCRIBIMOS EL PDF ---
            documento.archivo_pdf.save(documento.archivo_pdf.name, ContentFile(output_pdf.read()))

            FirmaDigital.objects.create(
                documento=documento, firmante=request.user, rol_firma='EMPLEADO', firmado=True,
                fecha_firma=fecha_actual, direccion_ip=ip_cliente, token_utilizado=sha256_hash[:6].upper()
            )

            documento.estado = 'COMPLETADO'
            documento.fecha_cierre = fecha_actual
            documento.save()
            messages.success(request, "¡Documento firmado! Se ha adjuntado el certificado legal al archivo.")
            
        except Exception:
            messages.error(request, "Error crítico al procesar el certificado de seguridad.")

        return redirect('documentos_personal')

    return render(request, 'intranet/documentos/confirmar_firma.html', {'documento': documento})

@login_required(login_url='login')
@solo_directivos
def eliminar_documento(request, doc_id):
    documento = get_object_or_404(DocumentoGenerado, id=doc_id)
    if documento.estado == 'PENDIENTE':
        documento.delete()
        messages.success(request, "Documento mal asignado eliminado con éxito.")
    else:
        messages.error(request, "No puedes eliminar un documento que ya ha sido firmado legalmente.")
    return redirect('documentos_admin')

@login_required(login_url='login')
@solo_directivos
def eliminar_plantilla(request, plantilla_id):
    plantilla = get_object_or_404(PlantillaDocumento, id=plantilla_id)
    plantilla.delete()
    messages.success(request, "Plantilla eliminada de la biblioteca.")
    return redirect('gestionar_plantillas')

@login_required(login_url='login')
@solo_directivos
def eliminar_documento_generado(request, doc_id):
    doc = get_object_or_404(DocumentoGenerado, id=doc_id)
    if doc.estado == 'PENDIENTE':
        doc.delete()
        messages.success(request, "Asignación eliminada correctamente.")
    else:
        messages.error(request, "No puedes eliminar un documento ya firmado.")
    return redirect('documentos_admin')