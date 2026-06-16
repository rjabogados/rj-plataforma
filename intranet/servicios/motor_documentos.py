import os
from datetime import date
from django.conf import settings
from docxtpl import DocxTemplate
from docx2pdf import convert
from django.core.files import File
from intranet.models import DocumentoGenerado

def generar_documento_para_colaborador(plantilla_obj, colaborador):
    """
    Toma un archivo Word, inyecta las variables del usuario, lo convierte a PDF
    y lo deposita en la Bóveda Virtual (DocumentoGenerado).
    """
    # 1. Cargamos el archivo Word de la plantilla
    ruta_plantilla = plantilla_obj.archivo_word.path
    doc = DocxTemplate(ruta_plantilla)

    # 2. Obtenemos el perfil laboral para acceder al DNI real y demás datos
    perfil = getattr(colaborador, 'perfil', None)

    dni_real = perfil.dni if perfil else colaborador.username
    rol_real = perfil.rol if perfil else 'No asignado'
    horario_real = perfil.tipo_horario if perfil else 'No asignado'
    negocio_real = perfil.negocio.nombre if perfil and perfil.negocio else 'No asignado'
    
    # Formatear la fecha de ingreso si existe
    if perfil and perfil.fecha_ingreso:
        fecha_ing_str = perfil.fecha_ingreso.strftime("%d/%m/%Y")
    else:
        fecha_ing_str = 'No registrada'

    # 3. Definimos las Variables (Lo que reemplazará a los {{ }} en el Word)
    contexto = {
        'nombre_completo': f"{colaborador.first_name} {colaborador.last_name}",
        'nombres': colaborador.first_name,
        'apellidos': colaborador.last_name,
        'dni': dni_real,
        'correo': colaborador.email,
        'rol': rol_real,
        'horario': horario_real,
        'negocio': negocio_real,
        'fecha_ingreso': fecha_ing_str,
        'fecha_hoy': date.today().strftime("%d/%m/%Y"),
        'fecha_actual': date.today().strftime("%d/%m/%Y"), # Alias adicional
        'empresa': 'RJ Abogados',
    }

    # 4. Inyectamos los datos en la plantilla
    doc.render(contexto)

    # 5. Guardamos el Word temporalmente
    carpeta_temp = os.path.join(settings.MEDIA_ROOT, 'temp')
    os.makedirs(carpeta_temp, exist_ok=True)
    
    nombre_base = f"{plantilla_obj.nombre.replace(' ', '_')}_{colaborador.username}"
    ruta_docx_temp = os.path.join(carpeta_temp, f"{nombre_base}.docx")
    ruta_pdf_temp = os.path.join(carpeta_temp, f"{nombre_base}.pdf")
    
    doc.save(ruta_docx_temp)

    # 6. Convertimos el Word modificado a PDF inalterable
    try:
        convert(ruta_docx_temp, ruta_pdf_temp)
    except Exception as e:
        print(f"Error al convertir a PDF: {e}")
        return None

    # 7. Lo registramos en la Bóveda Virtual de RJ Talent
    nuevo_doc = DocumentoGenerado.objects.create(
        colaborador=colaborador,
        plantilla_origen=plantilla_obj,
        titulo=f"{plantilla_obj.nombre} - {colaborador.first_name}",
        estado='PENDIENTE', 
        visible_para_empleado=True # ¡CORREGIDO! Ahora sí aparece de inmediato en su bóveda
    )

    # Guardamos el archivo físico PDF en el registro de la base de datos
    with open(ruta_pdf_temp, 'rb') as f:
        nuevo_doc.archivo_pdf.save(f"{nombre_base}.pdf", File(f))

    # Limpieza: Borramos los archivos temporales para no saturar tu disco
    os.remove(ruta_docx_temp)
    os.remove(ruta_pdf_temp)

    return nuevo_doc