from .auth import login_view, salir, inicio, perfil, dashboard

from .api import webhook_receptor

from .reclutamiento import (
    lista_candidatos, 
    obtener_candidato_ajax, 
    actualizar_candidato_ajax, 
    descartar_candidato_ajax,
    metricas_dashboard_ajax  # <--- ESTO ES LO QUE FALTA
)

from .asistencia import (
    sincronizar_sheets, control_asistencia, eliminar_asistencia, 
    procesar_huellero, visor_asistencia, modo_televisor
)

from .solicitudes import (
    tickets, tickets_admin, revisar_ticket, 
    vacaciones, vacaciones_admin, eliminar_vacaciones
)

from .documentos import (
    documentos_admin, gestionar_plantillas, documentos_personal, 
    firmar_documento, eliminar_documento, eliminar_plantilla, 
    eliminar_documento_generado
)

from .lms import (
    colaboradores, editar_colaborador, eliminar_colaborador, mapear_excel, procesar_excel_mapeado,
    induccion, induccion_admin, gestionar_onboarding, onboarding_admin,
    asignar_modulos_induccion, mi_induccion, actualizar_expediente, pasar_a_planilla,
    encuestas_personal, encuestas_admin, resultados_encuesta, exportar_encuesta,
    mensajeria, leer_mensaje, calendario, comunicados, gestor_comunicados,
    eliminar_comunicado, eliminar_evento, eliminar_candidato,
    activos, gestor_lms, academia, beneficios
)