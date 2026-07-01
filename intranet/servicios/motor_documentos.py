import re
from datetime import date
from django.conf import settings
from intranet.models import DocumentoGenerado

def generar_documento_para_colaborador(plantilla_obj, colaborador):
    """
    Genera documento HTML reemplazando variables dinámicas y guarda el resultado.
    """
    if not plantilla_obj.contenido_html:
        raise ValueError("La plantilla no tiene contenido HTML.")
        
    html_content = plantilla_obj.contenido_html

    # Obtener datos del colaborador
    perfil = getattr(colaborador, 'perfil', None)
    
    dni_real = perfil.dni if perfil else colaborador.username
    rol_real = perfil.rol if perfil else 'No asignado'
    horario_real = perfil.tipo_horario if perfil else 'No asignado'
    negocio_real = perfil.negocio.nombre if perfil and perfil.negocio else 'No asignado'
    area_real = perfil.area.nombre if perfil and perfil.area else 'No asignada'
    cargo_real = perfil.cargo.nombre if perfil and perfil.cargo else 'No asignado'
    sueldo_real = str(perfil.salario_mensual) if perfil and perfil.salario_mensual else '0.00'
    
    if perfil and perfil.fecha_ingreso:
        fecha_ing_str = perfil.fecha_ingreso.strftime("%d/%m/%Y")
    else:
        fecha_ing_str = 'No registrada'

    # Diccionario de variables
    contexto = {
        '{nombre_colaborador}': f"{colaborador.first_name} {colaborador.last_name}",
        '{nombres}': colaborador.first_name,
        '{apellidos}': colaborador.last_name,
        '{dni_colaborador}': dni_real,
        '{correo}': colaborador.email,
        '{cargo_colaborador}': cargo_real,
        '{area_colaborador}': area_real,
        '{sueldo_base}': sueldo_real,
        '{fecha_ingreso}': fecha_ing_str,
        '{fecha_actual}': date.today().strftime("%d/%m/%Y"),
        '{empresa}': 'RJ Abogados'
    }

    # Reemplazar todas las ocurrencias
    html_generado = html_content
    for key, value in contexto.items():
        html_generado = html_generado.replace(key, value)

    # Registrar en base de datos
    nuevo_doc = DocumentoGenerado.objects.create(
        colaborador=colaborador,
        plantilla_origen=plantilla_obj,
        titulo=f"{plantilla_obj.nombre} - {colaborador.first_name}",
        estado='PENDIENTE',
        visible_para_empleado=True,
        contenido_generado=html_generado
    )

    return nuevo_doc