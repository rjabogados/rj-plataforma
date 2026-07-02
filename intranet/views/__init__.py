from .auth import login_view, salir, inicio, guardar_atajos, perfil, perfil_publico, dashboard, dashboard_rrhh, exportar_directorio_rrhh, dashboard_supervisor, exportar_equipo_supervisor, perfil_admin, notificaciones, leer_notificacion, marcar_todas_leidas, notificaciones_push_ajax, menu_inicial

from .api import webhook_receptor

from .reclutamiento import (
    dashboard_reclutamiento,
    lista_candidatos, 
    obtener_candidato_ajax, 
    actualizar_candidato_ajax, 
    descartar_candidato_ajax,
    metricas_dashboard_ajax,
    registrar_contacto_ajax,
    exportar_candidatos_csv,
    eliminar_historial_ajax,
    importar_matriz_excel,
    procesar_mapeo_matriz
)

from .asistencia import (
    sincronizar_sheets, control_asistencia, eliminar_asistencia, 
    procesar_huellero, visor_asistencia, modo_televisor
)

from .busqueda import buscador_global

from .solicitudes import (
    tickets, tickets_admin, revisar_ticket, 
    vacaciones, vacaciones_admin, eliminar_vacaciones, eliminar_ticket, ver_adjunto_ticket, centro_ayuda,
    calendario_ausencias
)

from .documentos import documentos_admin, gestor_plantillas, editor_plantilla, documentos_personal, \
    firmar_documento, eliminar_plantilla, eliminar_documento_generado, \
    ver_documento_personal, ver_documento_admin

from .lms import (
    colaboradores, editar_colaborador, eliminar_colaborador, mapear_excel, procesar_mapeo_personal, procesar_mapeo_balotario,
    induccion, induccion_admin, gestionar_onboarding, onboarding_admin,
    asignar_modulos_induccion, mi_induccion, actualizar_expediente, pasar_a_planilla,
    encuestas_personal, encuestas_admin, resultados_encuesta, exportar_encuesta,
    mensajeria, leer_mensaje, calendario, comunicados, gestor_comunicados,
    eliminar_comunicado, eliminar_evento, eliminar_candidato,
    activos, gestor_lms, academia, beneficios, ver_leccion_pdf,
    ver_adjunto_mensaje, ver_adjunto_comunicado
)

from .cultura import muro_celebraciones, muro_kudos, catalogo_premios, admin_gamificacion
from .desempeno import dashboard_desempeno, mis_evaluaciones, evaluar_equipo, form_evaluacion