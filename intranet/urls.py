from django.urls import path
from . import views
from .views.reclutamiento import actualizar_estado_ajax, obtener_candidato_ajax, actualizar_candidato_ajax, descartar_candidato_ajax
from .views import lms

urlpatterns = [
    # ==========================================
    # NAVEGACIÓN BÁSICA E INICIO
    # ==========================================
    path('', views.inicio, name='inicio'),
    path('perfil/', views.perfil, name='perfil'),
    path('salir/', views.salir, name='salir'),
    path('login/', views.login_view, name='login'),

    # ==========================================
    # DIRECTORIO DE PERSONAL (RRHH)
    # ==========================================
    path('colaboradores/', views.colaboradores, name='colaboradores'),
    path('colaboradores/editar/<int:pk>/', views.editar_colaborador, name='editar_colaborador'),
    path('colaboradores/eliminar/<int:pk>/', views.eliminar_colaborador, name='eliminar_colaborador'),
    path('colaboradores/mapear-excel/', views.mapear_excel, name='mapear_excel'),
    path('colaboradores/procesar-mapeado/', lms.procesar_mapeo_balotario, name='procesar_mapeo_balotario'),

    # ==========================================
    # ONBOARDING CORPORATIVO (INDUCCIÓN)
    # ==========================================
    path('admin-onboarding/', views.onboarding_admin, name='onboarding_admin'),
    path('admin-onboarding/actualizar/<int:candidato_id>/', views.actualizar_expediente, name='actualizar_expediente'),
    path('admin-onboarding/contratar/<int:candidato_id>/', views.pasar_a_planilla, name='pasar_a_planilla'),
    path('admin-onboarding/asignar/<int:colab_id>/', views.asignar_modulos_induccion, name='asignar_modulos_induccion'),
    path('mi-induccion/', views.mi_induccion, name='mi_induccion'),
    path('onboarding/', views.induccion, name='induccion'),
    path('onboarding-admin/', views.induccion_admin, name='induccion_admin'),
    path('candidato/eliminar/<int:pk>/', views.eliminar_candidato, name='eliminar_candidato'),
    path('admin-onboarding/curso/<int:curso_id>/editar/', lms.editar_curso_induccion, name='editar_curso_induccion'),
    path('admin-onboarding/curso/<int:curso_id>/eliminar/', lms.eliminar_curso_induccion, name='eliminar_curso_induccion'),

    # ==========================================
    # ACADEMIA LMS (CAPACITACIÓN CONTINUA)
    # ==========================================
    path('academia/', views.academia, name='academia'),
    path('academia/gestor/', views.gestor_lms, name='gestor_lms'),
    path('academia/evaluacion/<int:evaluacion_id>/importar/', lms.importar_excel_balotario, name='importar_excel_balotario'),
    path('academia/evaluacion/previsualizar/', lms.previsualizar_y_guardar_balotario, name='previsualizar_balotario'),
    path('academia/rendir/<int:matricula_id>/', lms.rendir_evaluacion, name='rendir_evaluacion'),
    path('academia/curso/<int:curso_id>/editar/', lms.editar_curso_lms, name='editar_curso_lms'),
    path('academia/curso/<int:curso_id>/eliminar/', lms.eliminar_curso_lms, name='eliminar_curso_lms'),
    
    # --- RUTAS DE APRENDIZAJE: CLASES Y VIDEOS (NUEVAS) ---
    path('academia/curso/<int:curso_id>/', lms.detalle_curso, name='detalle_curso'),
    path('academia/leccion/<int:leccion_id>/', lms.ver_leccion, name='ver_leccion'),
    path('academia/leccion/<int:leccion_id>/completar/', lms.completar_leccion, name='completar_leccion'),

    # --- RUTAS DE GAMIFICACIÓN Y ANALÍTICA ---
    path('academia/evaluacion/<int:evaluacion_id>/resultados/', lms.resultados_evaluacion, name='resultados_evaluacion'),
    path('academia/matricula/<int:matricula_id>/reabrir/', lms.reabrir_examen, name='reabrir_examen'),
    path('academia/evaluacion/<int:evaluacion_id>/exportar/', lms.exportar_resultados_lms, name='exportar_resultados_lms'),
    path('academia/certificado/<int:matricula_id>/', lms.generar_certificado, name='generar_certificado'),

    # ==========================================
    # BÓVEDA DIGITAL Y DOCUMENTOS
    # ==========================================
    path('admin-documentos/despacho/', views.documentos_admin, name='documentos_admin'),
    path('admin-documentos/plantillas/', views.gestionar_plantillas, name='gestionar_plantillas'),
    path('documentos/borrar-asignacion/<int:doc_id>/', views.eliminar_documento_generado, name='eliminar_doc_generado'),
    path('plantillas/borrar-formato/<int:plantilla_id>/', views.eliminar_plantilla, name='eliminar_plantilla'),
    path('mis-documentos/', views.documentos_personal, name='documentos_personal'),
    path('mis-documentos/firmar/<int:doc_id>/', views.firmar_documento, name='firmar_documento'),

    # ==========================================
    # GESTIÓN DE TICKETS Y VACACIONES
    # ==========================================
    path('tickets/', views.tickets, name='tickets'),
    path('tickets-admin/', views.tickets_admin, name='tickets_admin'),
    path('tickets/revisar/<int:pk>/<str:estado>/', views.revisar_ticket, name='revisar_ticket'),
    path('vacaciones/', views.vacaciones, name='vacaciones'),
    path('vacaciones-admin/', views.vacaciones_admin, name='vacaciones_admin'),
    path('vacaciones/eliminar/<int:pk>/', views.eliminar_vacaciones, name='eliminar_vacaciones'),

    # ==========================================
    # ASISTENCIAS BIOMÉTRICAS
    # ==========================================
    path('asistencia/', views.control_asistencia, name='asistencia'),
    path('asistencia/sincronizar/', views.sincronizar_sheets, name='sincronizar_sheets'),
    path('asistencia/eliminar/<int:pk>/', views.eliminar_asistencia, name='eliminar_asistencia'),
    path('asistencia/procesar-huellero/', views.procesar_huellero, name='procesar_huellero'),
    path('asistencia/visor/', views.visor_asistencia, name='visor_asistencia'),

    # ==========================================
    # MOTOR DE ENCUESTAS
    # ==========================================
    path('encuestas/', views.encuestas_personal, name='encuestas_personal'),
    path('encuestas-control/', views.encuestas_admin, name='encuestas_admin'),
    path('encuestas/resultados/<int:pk>/', views.resultados_encuesta, name='resultados_encuesta'),
    path('encuestas/exportar/<int:pk>/', views.exportar_encuesta, name='exportar_encuesta'),

    # ==========================================
    # MENSAJERÍA Y CULTURA RJ
    # ==========================================
    path('mensajeria/', views.mensajeria, name='mensajeria'),
    path('mensajeria/leer/<int:pk>/', views.leer_mensaje, name='leer_mensaje'),
    path('comunicados/', views.comunicados, name='comunicados'),
    path('comunicados/eliminar/<int:pk>/', views.eliminar_comunicado, name='eliminar_comunicado'),
    path('gestor-anuncios/', views.gestor_comunicados, name='gestor_comunicados'),
    path('calendario/', views.calendario, name='calendario'),
    path('calendario/eliminar/<int:pk>/', views.eliminar_evento, name='eliminar_evento'),
    path('beneficios/', views.beneficios, name='beneficios'),

    # ==========================================
    # MÓDULOS SECUNDARIOS Y DASHBOARD
    # ==========================================
    path('dashboard/', views.dashboard, name='dashboard'),
    path('activos/', views.activos, name='activos'),
    path('televisor/', views.modo_televisor, name='modo_televisor'),
    path('api/webhook/', views.webhook_receptor, name='webhook_receptor'),
    path('reclutamiento/candidatos/', views.lista_candidatos, name='lista_candidatos'),
    path('api/actualizar-estado/', actualizar_estado_ajax, name='ajax_actualizar_estado'),
    path('api/obtener-candidato/<int:candidato_id>/', obtener_candidato_ajax, name='api_obtener_candidato'),
    path('api/actualizar-candidato/', actualizar_candidato_ajax, name='api_actualizar_candidato'),
    path('api/descartar-candidato/', descartar_candidato_ajax, name='api_descartar_candidato'),
    path('api/metricas-dashboard/', views.metricas_dashboard_ajax, name='api_metricas_dashboard'),
]