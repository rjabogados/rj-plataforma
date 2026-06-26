import os
import mimetypes
from datetime import date
from django.conf import settings
from docxtpl import DocxTemplate
from django.core.files import File
from docx2pdf import convert
from django.core.files import File
from intranet.models import DocumentoGenerado

def generar_documento_para_colaborador(plantilla_obj, colaborador):
    """
    Genera documento de forma segura, validando rutas y tipos de archivo.
    """
    
    # 1. Validación de seguridad: Verificar que la plantilla existe
    ruta_plantilla = plantilla_obj.archivo_word.path
    
    # ✅ Validar que la ruta está dentro de MEDIA_ROOT
    ruta_plantilla = os.path.abspath(ruta_plantilla)
    media_root = os.path.abspath(settings.MEDIA_ROOT)
    
    if not ruta_plantilla.startswith(media_root):
        raise ValueError("Ruta de plantilla inválida")
    
    # ✅ Validar que el archivo existe y es accesible
    if not os.path.isfile(ruta_plantilla):
        raise FileNotFoundError(f"Plantilla no encontrada: {ruta_plantilla}")
    
    # ✅ Validar tipo MIME
    mime_type, _ = mimetypes.guess_type(ruta_plantilla)
    allowed_mimes = [
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword'
    ]
    if mime_type not in allowed_mimes:
        raise ValueError("Tipo de archivo no permitido")
    
    try:
        doc = DocxTemplate(ruta_plantilla)
    except Exception as e:
        raise ValueError(f"Error al leer plantilla: {str(e)}")

    # 2. Obtener datos del colaborador de forma segura
    perfil = getattr(colaborador, 'perfil', None)
    
    dni_real = perfil.dni if perfil else colaborador.username
    rol_real = perfil.rol if perfil else 'No asignado'
    horario_real = perfil.tipo_horario if perfil else 'No asignado'
    negocio_real = perfil.negocio.nombre if perfil and perfil.negocio else 'No asignado'
    area_real = perfil.area.nombre if perfil and perfil.area else 'No asignada'
    cargo_real = perfil.cargo.nombre if perfil and perfil.cargo else 'No asignado'
    subcartera_real = perfil.subcartera if perfil and perfil.subcartera else 'No asignada'
    
    if perfil and perfil.fecha_ingreso:
        fecha_ing_str = perfil.fecha_ingreso.strftime("%d/%m/%Y")
    else:
        fecha_ing_str = 'No registrada'

    # 3. Contexto seguro con límites de tamaño
    contexto = {
        'nombre_completo': f"{colaborador.first_name} {colaborador.last_name}"[:200],
        'nombres': colaborador.first_name[:100],
        'apellidos': colaborador.last_name[:100],
        'dni': dni_real[:20],
        'correo': colaborador.email[:200],
        'rol': rol_real[:100],
        'area': area_real[:150],
        'cargo': cargo_real[:150],
        'horario': horario_real[:50],
        'negocio': negocio_real[:150],
        'subcartera': subcartera_real[:100],
        'fecha_ingreso': fecha_ing_str,
        'fecha_hoy': date.today().strftime("%d/%m/%Y"),
        'fecha_actual': date.today().strftime("%d/%m/%Y"),
        'empresa': 'RJ Abogados',
    }

    doc.render(contexto)

    # 4. Crear nombres seguros sin caracteres especiales
    import re
    nombre_plantilla_limpio = re.sub(r'[^a-zA-Z0-9_-]', '_', plantilla_obj.nombre)
    usuario_limpio = re.sub(r'[^a-zA-Z0-9_-]', '_', colaborador.username)
    nombre_base = f"{nombre_plantilla_limpio}_{usuario_limpio}_{date.today().strftime('%Y%m%d')}"
    
    # 5. Carpeta temporal segura
    carpeta_temp = os.path.join(settings.MEDIA_ROOT, 'temp')
    os.makedirs(carpeta_temp, exist_ok=True)
    
    # Validar que carpeta_temp está dentro de MEDIA_ROOT
    carpeta_temp = os.path.abspath(carpeta_temp)
    if not carpeta_temp.startswith(media_root):
        raise ValueError("Ruta temporal inválida")
    
    ruta_docx_temp = os.path.join(carpeta_temp, f"{nombre_base}.docx")
    ruta_pdf_temp = os.path.join(carpeta_temp, f"{nombre_base}.pdf")
    
    # Protección contra sobrescritura
    contador = 1
    while os.path.exists(ruta_docx_temp):
        nombre_base = f"{nombre_plantilla_limpio}_{usuario_limpio}_{date.today().strftime('%Y%m%d')}_{contador}"
        ruta_docx_temp = os.path.join(carpeta_temp, f"{nombre_base}.docx")
        ruta_pdf_temp = os.path.join(carpeta_temp, f"{nombre_base}.pdf")
        contador += 1
    
    doc.save(ruta_docx_temp)

    # 6. Convertir a PDF
    try:
        convert(ruta_docx_temp, ruta_pdf_temp)
    except Exception as e:
        # Limpiar temporales
        if os.path.exists(ruta_docx_temp):
            os.remove(ruta_docx_temp)
        raise ValueError(f"Error al convertir PDF: {str(e)}")

    # 7. Registrar en base de datos
    nuevo_doc = DocumentoGenerado.objects.create(
        colaborador=colaborador,
        plantilla_origen=plantilla_obj,
        titulo=f"{plantilla_obj.nombre} - {colaborador.first_name}",
        estado='PENDIENTE',
        visible_para_empleado=True
    )

    # 8. Guardar archivo
    try:
        with open(ruta_pdf_temp, 'rb') as f:
            nuevo_doc.archivo_pdf.save(f"{nombre_base}.pdf", File(f))
    except Exception as e:
        nuevo_doc.delete()
        raise ValueError(f"Error al guardar PDF: {str(e)}")
    finally:
        # Limpiar archivos temporales
        for ruta in [ruta_docx_temp, ruta_pdf_temp]:
            if os.path.exists(ruta):
                try:
                    os.remove(ruta)
                except:
                    pass

    return nuevo_doc