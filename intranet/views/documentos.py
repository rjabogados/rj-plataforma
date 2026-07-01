import hashlib
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from intranet.models import CategoriaDocumento, PlantillaDocumento, DocumentoGenerado, FirmaDigital, Colaborador, Notificacion
from intranet.servicios.motor_documentos import generar_documento_para_colaborador
from .utils import solo_directivos, obtener_ip_cliente, filtrar_colaboradores, filtros_personal_disponibles

@login_required(login_url='login')
@solo_directivos
def gestor_plantillas(request):
    """Biblioteca digital de plantillas HTML."""
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'crear_categoria':
            nombre_categoria = (request.POST.get('nombre_categoria') or '').strip()
            requiere_firma = request.POST.get('requiere_firma') == 'on'
            if not nombre_categoria:
                messages.error(request, 'Debes indicar un nombre para la categoria.')
                return redirect('gestor_plantillas')

            categoria, creada = CategoriaDocumento.objects.get_or_create(
                nombre=nombre_categoria,
                defaults={'requiere_firma': requiere_firma},
            )
            if creada:
                messages.success(request, f"Categoria '{nombre_categoria}' creada correctamente.")
            else:
                categoria.requiere_firma = requiere_firma
                categoria.save(update_fields=['requiere_firma'])
                messages.info(request, f"La categoria '{nombre_categoria}' ya existia y se actualizo su configuracion.")
            return redirect('gestor_plantillas')

        if action == 'eliminar_categoria':
            categoria_id = request.POST.get('categoria_id')
            categoria = CategoriaDocumento.objects.filter(id=categoria_id).first()
            if not categoria:
                messages.error(request, 'Categoria no encontrada.')
                return redirect('gestor_plantillas')
            nombre_categoria = categoria.nombre
            categoria.delete()
            messages.success(request, f"Categoria '{nombre_categoria}' eliminada.")
            return redirect('gestor_plantillas')

        if action == 'crear':
            nombre = (request.POST.get('nombre') or '').strip()
            categoria_id = request.POST.get('categoria_id')
            nueva_categoria = (request.POST.get('nueva_categoria') or '').strip()

            categoria = None
            if nueva_categoria:
                categoria, _ = CategoriaDocumento.objects.get_or_create(nombre=nueva_categoria)
            elif categoria_id:
                categoria = CategoriaDocumento.objects.filter(id=categoria_id).first()
            
            if nombre:
                nueva_plantilla = PlantillaDocumento.objects.create(
                    nombre=nombre, 
                    categoria=categoria, 
                    creado_por=request.user,
                    contenido_html="<p>Escribe tu documento aquí...</p>"
                )
                return redirect('editor_plantilla', plantilla_id=nueva_plantilla.id)
            messages.error(request, 'Debes indicar el nombre del documento para crear la plantilla.')
            return redirect('gestor_plantillas')
                
    plantillas = PlantillaDocumento.objects.select_related('categoria', 'creado_por').all().order_by('-fecha_modificacion')
    categorias = CategoriaDocumento.objects.all().order_by('nombre')
    return render(request, 'intranet/documentos/gestor_plantillas.html', {
        'plantillas': plantillas,
        'categorias': categorias,
    })

@login_required(login_url='login')
@solo_directivos
def editor_plantilla(request, plantilla_id):
    """Editor enriquecido de la plantilla."""
    plantilla = get_object_or_404(PlantillaDocumento, id=plantilla_id)
    
    if request.method == 'POST':
        contenido = request.POST.get('contenido_html')
        plantilla.contenido_html = contenido
        plantilla.save()
        messages.success(request, "Plantilla guardada correctamente.")
        return redirect('gestor_plantillas')
        
    return render(request, 'intranet/documentos/editor_plantilla.html', {'plantilla': plantilla})

@login_required(login_url='login')
@solo_directivos
def eliminar_plantilla(request, plantilla_id):
    plantilla = get_object_or_404(PlantillaDocumento, id=plantilla_id)
    plantilla.delete()
    messages.success(request, "Plantilla eliminada.")
    return redirect('gestor_plantillas')

@login_required(login_url='login')
@solo_directivos
def documentos_admin(request):
    """Panel de despacho para generar contratos basados en plantillas HTML."""
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
            
            try:
                nuevo_doc = generar_documento_para_colaborador(plantilla, colaborador)
                
                # Notificación Push Interna
                Notificacion.objects.create(
                    usuario=colaborador,
                    titulo="Nuevo Documento para Firma",
                    detalle=f"Tienes un nuevo documento pendiente de firma: {plantilla.nombre}",
                    tipo='ALERTA',
                    url_destino=f"/mis-documentos/firmar/{nuevo_doc.id}/"
                )
                
                # Enviar Correo
                if colaborador.email:
                    send_mail(
                        subject='Nuevo documento pendiente de firma digital',
                        message=f'Hola {colaborador.first_name},\nTienes un nuevo documento ("{plantilla.nombre}") pendiente de firma en la plataforma.\n\nPor favor ingresa para firmarlo digitalmente.',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[colaborador.email],
                        fail_silently=True
                    )
                
                messages.success(request, f"¡Éxito! Documento '{plantilla.nombre}' generado y enviado a {colaborador.first_name}.")
            except Exception as e:
                messages.error(request, f"Error al generar documento: {str(e)}")
                
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
def documentos_personal(request):
    """Bóveda del trabajador."""
    mis_docs = DocumentoGenerado.objects.filter(colaborador=request.user).order_by('-fecha_emision')
    return render(request, 'intranet/documentos/documentos_personal.html', {'documentos': mis_docs})

@login_required(login_url='login')
def ver_documento_personal(request, doc_id):
    documento = get_object_or_404(DocumentoGenerado, id=doc_id, colaborador=request.user)
    return render(request, 'intranet/documentos/visor_documento.html', {'documento': documento})

@login_required(login_url='login')
@solo_directivos
def ver_documento_admin(request, doc_id):
    documento = get_object_or_404(DocumentoGenerado, id=doc_id)
    return render(request, 'intranet/documentos/visor_documento.html', {'documento': documento})

@login_required(login_url='login')
def firmar_documento(request, doc_id):
    """Firma digital insertando el certificado al final del HTML."""
    documento = get_object_or_404(DocumentoGenerado, id=doc_id, colaborador=request.user)

    if request.method == 'POST' and documento.estado == 'PENDIENTE':
        acepto_terminos = request.POST.get('acepto_terminos') == 'on'
        if not acepto_terminos:
            return redirect('firmar_documento', doc_id=doc_id)

        try:
            ip_cliente = obtener_ip_cliente(request)
            fecha_actual = timezone.now()
            fecha_str = fecha_actual.strftime("%d/%m/%Y a las %H:%M:%S")
            
            base_string = f"{documento.id}-{request.user.username}-{fecha_str}-{ip_cliente}"
            sha256_hash = hashlib.sha256(base_string.encode('utf-8')).hexdigest()
            token = sha256_hash[:8].upper()

            # Certificado HTML
            certificado_html = f"""
            <div style="margin-top: 50px; padding: 20px; border: 2px solid #28a745; border-radius: 8px; background-color: #f8fff9;">
                <h3 style="color: #28a745; margin-top:0;">✅ CERTIFICADO DE FIRMA ELECTRÓNICA</h3>
                <p><strong>RJ Abogados - Plataforma Talent</strong></p>
                <hr>
                <p>Documento firmado digitalmente por:</p>
                <p><strong>Nombre:</strong> {request.user.first_name} {request.user.last_name}</p>
                <p><strong>DNI / Identificación:</strong> {request.user.username}</p>
                <p><strong>Rastro Forense de Seguridad:</strong></p>
                <ul>
                    <li><strong>Fecha y Hora Exacta:</strong> {fecha_str}</li>
                    <li><strong>Dirección IP de Origen:</strong> {ip_cliente}</li>
                    <li><strong>Token Hash de Seguridad:</strong> {token}</li>
                </ul>
                <p style="font-size: 0.85em; color: #555;">Este anexo garantiza la validez legal y autoría del documento. Cualquier alteración posterior invalidará la firma.</p>
            </div>
            """
            
            documento.contenido_generado = documento.contenido_generado + certificado_html
            documento.estado = 'COMPLETADO'
            documento.fecha_cierre = fecha_actual
            documento.save()

            FirmaDigital.objects.create(
                documento=documento, firmante=request.user, rol_firma='EMPLEADO', firmado=True,
                fecha_firma=fecha_actual, direccion_ip=ip_cliente, token_utilizado=token
            )

            messages.success(request, "¡Documento firmado! Se ha adjuntado el certificado legal al archivo.")
            
        except Exception as e:
            messages.error(request, f"Error crítico al procesar la firma: {str(e)}")

        return redirect('documentos_personal')

    return render(request, 'intranet/documentos/confirmar_firma.html', {'documento': documento})

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