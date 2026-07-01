from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

# Importaciones de vistas
from . import views
from .views.reclutamiento import actualizar_estado_ajax, obtener_candidato_ajax, actualizar_candidato_ajax, descartar_candidato_ajax
from .views import lms, ia_views
from intranet.views.lms import dashboard_resultados, crear_curso_avanzado, crear_curso_induccion

# ==========================================
# ESPACIO DE NOMBRES (CRÍTICO PARA REDIRECCIONES)
# ==========================================

urlpatterns = [
    # ==========================================
    # NAVEGACIÓN BÁSICA E INICIO
    # ==========================================
    path('', views.inicio, name='inicio'),
    path('menu-inicial/', views.menu_inicial, name='menu_inicial'),
    path('configurar-atajos/', views.guardar_atajos, name='guardar_atajos'),
    path('buscar/', views.buscador_global, name='buscar'),
    path('perfil/', views.perfil, name='perfil'),
    path('perfil-admin/', views.perfil_admin, name='perfil_admin'),
    path('notificaciones/', views.notificaciones, name='notificaciones'),
    path('notificaciones/leer/<int:pk>/', views.leer_notificacion, name='leer_notificacion'),
    path('notificaciones/marcar-todas/', views.marcar_todas_leidas, name='marcar_todas_leidas'),
    path('api/notificaciones-push/', views.notificaciones_push_ajax, name='notificaciones_push_ajax'),
    path('salir/', views.salir, name='salir'),
    path('login/', views.login_view, name='login'),

    # ==========================================
    # DIRECTORIO DE PERSONAL (RRHH)
    # ==========================================
    path('colaboradores/', views.colaboradores, name='colaboradores'),
    path('colaboradores/editar/<int:pk>/', views.editar_colaborador, name='editar_colaborador'),
    path('colaboradores/eliminar/<int:pk>/', views.eliminar_colaborador, name='eliminar_colaborador'),
    path('colaboradores/mapear-excel/', views.mapear_excel, name='mapear_excel'),
    path('colaboradores/procesar-mapeado-personal/', lms.procesar_mapeo_personal, name='procesar_mapeo_personal'),
    path('colaboradores/procesar-mapeado/', lms.procesar_mapeo_balotario, name='procesar_mapeo_balotario'),
    path('rrhh/organigrama/', lms.organigrama_empresa, name='organigrama_empresa'),
    path('rrhh/sincronizar-taxonomia/', lms.sincronizar_taxonomia, name='sincronizar_taxonomia'),

    # ==========================================
    # ONBOARDING CORPORATIVO (INDUCCIÓN)
    # ==========================================
    path('admin-onboarding/', views.onboarding_admin, name='onboarding_admin'),
    path('admin-onboarding/actualizar/<int:candidato_id>/', views.actualizar_expediente, name='actualizar_expediente'),
    path('admin-onboarding/contratar/<int:candidato_id>/', views.pasar_a_planilla, name='pasar_a_planilla'),
    path('admin-onboarding/asignar/<int:colab_id>/', views.asignar_modulos_induccion, name='asignar_modulos_induccion'),
    path('admin-onboarding/crear-ruta/', lms.crear_ruta_induccion_view, name='crear_ruta_onboarding'),
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

    # ==========================================
    # CULTURA Y RECONOCIMIENTOS
    # ==========================================
    path('cultura/cumpleanos/', views.muro_celebraciones, name='muro_celebraciones'),
    path('cultura/kudos/', views.muro_kudos, name='muro_kudos'),
    path('cultura/premios/', views.catalogo_premios, name='catalogo_premios'),
    path('cultura/admin-gamificacion/', views.admin_gamificacion, name='admin_gamificacion'),

    path('academia/rendir/<int:matricula_id>/', lms.rendir_evaluacion, name='rendir_evaluacion'),
    path('academia/curso/<int:curso_id>/editar/', lms.editar_curso_lms, name='editar_curso_lms'),
    path('academia/curso/<int:curso_id>/eliminar/', lms.eliminar_curso_lms, name='eliminar_curso_lms'),
    path('academia/curso/<int:curso_id>/versionar/', lms.duplicar_version_curso, name='duplicar_version_curso'),
    
    # --- NUEVAS RUTAS DE GESTIÓN DETALLADA LMS ---
    path('academia/gestor/categoria/<int:pk>/editar/', lms.editar_categoria_lms, name='editar_categoria_lms'),
    path('academia/gestor/categoria/<int:pk>/eliminar/', lms.eliminar_categoria_lms, name='eliminar_categoria_lms'),
    path('academia/curso/<int:pk>/curriculum/', lms.curso_curriculum, name='curso_curriculum'),
    path('academia/leccion/<int:pk>/editar/', lms.editar_leccion_lms, name='editar_leccion_lms'),
    path('academia/leccion/<int:pk>/eliminar/', lms.eliminar_leccion_lms, name='eliminar_leccion_lms'),
    path('academia/evaluacion/<int:pk>/eliminar/', lms.eliminar_evaluacion_lms, name='eliminar_evaluacion_lms'),
    
    # --- RUTAS DE APRENDIZAJE: CLASES Y VIDEOS (NUEVAS) ---
    path('academia/curso/<int:curso_id>/', lms.detalle_curso, name='detalle_curso'),
    path('academia/leccion/<int:leccion_id>/', lms.ver_leccion, name='ver_leccion'),
    path('academia/leccion/<int:leccion_id>/pdf/', views.ver_leccion_pdf, name='ver_leccion_pdf'),
    path('academia/leccion/<int:leccion_id>/completar/', lms.completar_leccion, name='completar_leccion'),

    # --- RUTAS DE GAMIFICACIÓN Y ANALÍTICA ---
    path('academia/evaluacion/<int:evaluacion_id>/resultados/', lms.resultados_evaluacion, name='resultados_evaluacion'),
    path('academia/matricula/<int:matricula_id>/reabrir/', lms.reabrir_examen, name='reabrir_examen'),
    path('academia/evaluacion/<int:evaluacion_id>/exportar/', lms.exportar_resultados_lms, name='exportar_resultados_lms'),
    path('academia/certificado/<int:matricula_id>/', lms.generar_certificado, name='generar_certificado'),
    path('academia/certificado/verificar/<str:codigo>/', lms.verificar_certificado, name='verificar_certificado'),
    path('lms/dashboard/', dashboard_resultados, name='dashboard_resultados'),
    path('lms/crear-curso/', crear_curso_avanzado, name='crear_curso_avanzado'),
    path('lms/editar-curso/<int:curso_id>/', crear_curso_avanzado, name='editar_curso_avanzado'),
    path('lms/api/curso/<int:curso_id>/lecciones/', lms.api_gestionar_lecciones, name='api_gestionar_lecciones'),
    path('induccion/modulo/crear/', lms.crear_curso_induccion, name='crear_curso_induccion'),
    path('induccion/modulo/editar/<int:curso_id>/', lms.crear_curso_induccion, name='editar_curso_induccion_stepper'),

    # ==========================================
    # BÓVEDA DIGITAL Y DOCUMENTOS
    # ==========================================
    path('admin-documentos/despacho/', views.documentos_admin, name='documentos_admin'),
    path('admin-documentos/plantillas/', views.gestor_plantillas, name='gestor_plantillas'),
    path('admin-documentos/plantillas/<int:plantilla_id>/editar/', views.editor_plantilla, name='editor_plantilla'),
    path('admin-documentos/ver/<int:doc_id>/', views.ver_documento_admin, name='ver_documento_admin'),
    path('documentos/borrar-asignacion/<int:doc_id>/', views.eliminar_documento_generado, name='eliminar_doc_generado'),
    path('plantillas/borrar-formato/<int:plantilla_id>/', views.eliminar_plantilla, name='eliminar_plantilla'),
    path('mis-documentos/', views.documentos_personal, name='documentos_personal'),
    path('mis-documentos/ver/<int:doc_id>/', views.ver_documento_personal, name='ver_documento_personal'),
    path('mis-documentos/firmar/<int:doc_id>/', views.firmar_documento, name='firmar_documento'),

    # ==========================================
    # CENTRO DE AYUDA, TICKETS Y VACACIONES
    # ==========================================
    path('centro-ayuda/', views.centro_ayuda, name='centro_ayuda'),
    path('tickets/', views.tickets, name='tickets'),
    path('tickets/<int:pk>/eliminar/', views.eliminar_ticket, name='eliminar_ticket'),
    path('tickets-admin/', views.tickets_admin, name='tickets_admin'),
    path('tickets/adjunto/<int:pk>/', views.ver_adjunto_ticket, name='ver_adjunto_ticket'),
    path('tickets/revisar/<int:pk>/<str:estado>/', views.revisar_ticket, name='revisar_ticket'),
    path('vacaciones/', views.vacaciones, name='vacaciones'),
    path('vacaciones/eliminar/<int:pk>/', views.eliminar_vacaciones, name='eliminar_vacaciones'),
    path('vacaciones-admin/', views.vacaciones_admin, name='vacaciones_admin'),
    path('calendario-ausencias/', views.calendario_ausencias, name='calendario_ausencias'),

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
    path('encuestas/crear/', lms.crear_encuesta_view, name='crear_encuesta'),
    path('encuestas/cerrar/<int:pk>/', lms.cerrar_encuesta, name='cerrar_encuesta'),
    path('encuestas/abrir/<int:pk>/', lms.abrir_encuesta, name='abrir_encuesta'),
    path('encuestas/eliminar/<int:pk>/', lms.eliminar_encuesta, name='eliminar_encuesta'),
    path('encuestas/resultados/<int:pk>/', views.resultados_encuesta, name='resultados_encuesta'),
    path('encuestas/exportar/<int:pk>/', views.exportar_encuesta, name='exportar_encuesta'),

    # ==========================================
    # MENSAJERÍA Y CULTURA RJ
    # ==========================================
    path('mensajeria/', views.mensajeria, name='mensajeria'),
    path('mensajeria/leer/<int:pk>/', views.leer_mensaje, name='leer_mensaje'),
    path('mensajeria/adjunto/<int:pk>/', views.ver_adjunto_mensaje, name='ver_adjunto_mensaje'),
    path('comunicados/', views.comunicados, name='comunicados'),
    path('comunicados/adjunto/<int:pk>/', views.ver_adjunto_comunicado, name='ver_adjunto_comunicado'),
    path('comunicados/eliminar/<int:pk>/', views.eliminar_comunicado, name='eliminar_comunicado'),
    path('gestor-anuncios/', views.gestor_comunicados, name='gestor_comunicados'),
    path('calendario/', views.calendario, name='calendario'),
    path('calendario/eliminar/<int:pk>/', views.eliminar_evento, name='eliminar_evento'),
    path('beneficios/', views.beneficios, name='beneficios'),

    # ==========================================
    # MÓDULOS SECUNDARIOS Y DASHBOARD
    # ==========================================
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/rrhh/', views.dashboard_rrhh, name='dashboard_rrhh'),
    path('dashboard/rrhh/exportar-directorio/', views.exportar_directorio_rrhh, name='exportar_directorio_rrhh'),
    path('dashboard/supervisor/', views.dashboard_supervisor, name='dashboard_supervisor'),
    path('dashboard/supervisor/exportar-equipo/', views.exportar_equipo_supervisor, name='exportar_equipo_supervisor'),
    path('activos/', views.activos, name='activos'),
    path('televisor/', views.modo_televisor, name='modo_televisor'),
    path('api/webhook/', views.webhook_receptor, name='webhook_receptor'),
    path('reclutamiento/dashboard/', views.dashboard_reclutamiento, name='dashboard_reclutamiento'),
    path('reclutamiento/exportar/', views.exportar_candidatos_csv, name='exportar_candidatos'),
    path('reclutamiento/importar/', views.importar_matriz_excel, name='importar_matriz_excel'),
    path('reclutamiento/importar/procesar/', views.procesar_mapeo_matriz, name='procesar_mapeo_matriz'),
    path('reclutamiento/candidatos/', views.lista_candidatos, name='lista_candidatos'),
    path('reclutamiento/candidatos/exportar/', views.exportar_candidatos_csv, name='exportar_candidatos'),
    path('api/actualizar-estado/', actualizar_estado_ajax, name='ajax_actualizar_estado'),
    path('api/obtener-candidato/<int:candidato_id>/', obtener_candidato_ajax, name='api_obtener_candidato'),
    path('api/actualizar-candidato/', actualizar_candidato_ajax, name='api_actualizar_candidato'),
    path('api/registrar-contacto/', views.registrar_contacto_ajax, name='api_registrar_contacto'),
    path('api/descartar-candidato/', descartar_candidato_ajax, name='api_descartar_candidato'),
    path('api/eliminar-historial/', views.eliminar_historial_ajax, name='api_eliminar_historial'),
    path('api/metricas-dashboard/', views.metricas_dashboard_ajax, name='api_metricas_dashboard'),

    # ==========================================
    # MÓDULO DE INTELIGENCIA ARTIFICIAL (IA)
    # ==========================================
    path('curso/<int:curso_id>/generar-examen/', ia_views.generar_examen_ia, name='generar_examen_ia'),

    # ==========================================
    # EVALUACIONES DE DESEMPEÑO
    # ==========================================
    path('desempeno/', views.dashboard_desempeno, name='dashboard_desempeno'),
    path('mis-evaluaciones/', views.mis_evaluaciones, name='mis_evaluaciones'),
    path('evaluar-equipo/', views.evaluar_equipo, name='evaluar_equipo'),
    path('evaluacion/<int:eval_id>/', views.form_evaluacion, name='form_evaluacion'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)