import csv
from datetime import date, datetime, timedelta
from django.shortcuts import render, redirect
from django.shortcuts import get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponse

# Importamos los modelos desde la carpeta superior
from intranet.models import (
    Comunicado, Colaborador, Ticket, SolicitudVacaciones, Asistencia, DocumentoGenerado,
    DocumentoPersonal, MensajeInterno, EventoCalendario, MatriculaCurso, RespuestaEncuesta,
    CandidatoOnboarding
)
# Importamos nuestras herramientas de seguridad
from .utils import solo_directivos, solo_supervisores

from django.core.cache import cache

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        # Generar clave de cache para este usuario
        cache_key = f'login_attempts_{username}'
        attempts = cache.get(cache_key, 0)
        
        # Si excedió los intentos (ej. 5), bloqueamos por 15 minutos (900 seg)
        if attempts >= 5:
            return render(request, 'intranet/auth/login.html', {
                'error': 'Cuenta bloqueada temporalmente por demasiados intentos fallidos. Intente nuevamente en 15 minutos.'
            })
            
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_active:
                # Login exitoso: Limpiamos los intentos
                cache.delete(cache_key)
                login(request, user)
                return redirect('inicio')
            else:
                return render(request, 'intranet/auth/login.html', {'error': 'Cuenta deshabilitada. Contacte a soporte.'})
        else:
            # Login fallido: incrementamos el contador
            cache.set(cache_key, attempts + 1, timeout=900)
            return render(request, 'intranet/auth/login.html', {'error': 'Usuario o contraseña incorrectos'})
            
    return render(request, 'intranet/auth/login.html')

@login_required
def perfil(request):
    perfil = getattr(request.user, 'perfil', None)
    password_form = PasswordChangeForm(request.user)

    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'datos' and perfil:
            perfil.descripcion_perfil = request.POST.get('descripcion_perfil', '').strip() or None
            perfil.permitir_mensajes_cumpleanos = request.POST.get('permitir_mensajes_cumpleanos') == 'on'
            if request.FILES.get('foto_perfil'):
                perfil.foto_perfil = request.FILES['foto_perfil']
            perfil.save()
            messages.success(request, 'Tu perfil se actualizó correctamente.')
            return redirect('perfil')

        if accion == 'password':
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Tu contraseña se cambió correctamente.')
                return redirect('perfil')
            messages.error(request, 'Revisa los campos de contraseña e inténtalo nuevamente.')

    return render(request, 'intranet/rrhh/perfil.html', {
        'perfil': perfil,
        'password_form': password_form,
    })

def salir(request):
    logout(request)
    return redirect('login')

@login_required(login_url='login')
def inicio(request):
    # Lógica que ya tengas (como obtener los comunicados)
    comunicados = Comunicado.objects.filter(activo=True).order_by('-fecha_publicacion')[:5]
    
    # 1. Cálculos para el Panel de Control Administrativo
    total_colaboradores = Colaborador.objects.filter(user__is_active=True).count()
    tickets_pendientes = Ticket.objects.filter(estado='PENDIENTE').count()
    
    # 2. Cálculos para el Espacio Personal (Métricas del usuario actual)
    mis_documentos = DocumentoGenerado.objects.filter(colaborador=request.user, estado='PENDIENTE').count()
    perfil = getattr(request.user, 'perfil', None)
    notificaciones_no_leidas = request.user.notificaciones.filter(leida=False).count()

    # 3. Atajos configurables
    mis_atajos = []
    if user_has_special_permissions(request.user, perfil):
        # Verificar en base de datos
        configurados = request.user.atajos_configurados.all().order_by('orden')
        if configurados.exists():
            mis_atajos = configurados
        else:
            # Por defecto mostrar algunos
            mis_atajos = [] # El template puede manejar vacíos si queremos

    # 4. Enviar las variables al HTML
    context = {
        'comunicados': comunicados,
        'total_colaboradores': total_colaboradores,
        'tickets_pendientes': tickets_pendientes,
        'vacaciones_pendientes': SolicitudVacaciones.objects.filter(estado='PENDIENTE').count(),
        'mis_documentos': mis_documentos,
        'perfil': perfil,
        'notificaciones_no_leidas': notificaciones_no_leidas,
        'mis_atajos': mis_atajos,
        'tiene_permisos_especiales': user_has_special_permissions(request.user, perfil)
    }
    
    return render(request, 'intranet/dashboard/inicio.html', context)

def user_has_special_permissions(user, perfil):
    if user.is_superuser: return True
    if not perfil: return False
    return perfil.es_directivo or perfil.es_supervisor or perfil.es_calidad

from django.http import JsonResponse
import json

@login_required(login_url='login')
def guardar_atajos(request):
    if request.method == 'POST':
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                atajos = data.get('atajos', [])
            else:
                atajos = request.POST.getlist('atajo')
            
            # Borrar atajos antiguos
            request.user.atajos_configurados.all().delete()
            
            # Crear nuevos
            from intranet.models.rrhh_core import AtajoUsuario
            
            # Mapeo de info para seguridad
            diccionario_rutas = {
                'colaboradores': ('Directorio Personal', 'bi-people-fill', 'info'),
                'asistencia': ('Control Asistencias', 'bi-fingerprint', 'warning'),
                'documentos_admin': ('Bóveda Documental', 'bi-folder-fill', 'success'),
                'vacaciones_admin': ('Gestión Vacaciones', 'bi-airplane-engines-fill', 'primary'),
                'encuestas_admin': ('Gestor de Encuestas', 'bi-bar-chart-fill', 'danger'),
                'induccion_admin': ('Rutas Inducción', 'bi-map-fill', 'info'),
                'gestor_lms': ('Academia LMS', 'bi-mortarboard-fill', 'warning'),
                'dashboard_rrhh': ('Métricas RRHH', 'bi-graph-up', 'success'),
                'dashboard_supervisor': ('Panel de Equipo', 'bi-diagram-3-fill', 'primary'),
                'muro_kudos': ('Muro de Cultura', 'bi-balloon-heart-fill', 'danger'),
                'centro_ayuda': ('Centro de Ayuda', 'bi-headset', 'info'),
            }
            
            for index, url_name in enumerate(atajos):
                if url_name in diccionario_rutas:
                    AtajoUsuario.objects.create(
                        user=request.user,
                        url_name=url_name,
                        nombre=diccionario_rutas[url_name][0],
                        icono=diccionario_rutas[url_name][1],
                        color=diccionario_rutas[url_name][2],
                        orden=index
                    )
            
            if request.content_type == 'application/json':
                return JsonResponse({'status': 'success'})
            
            from django.contrib import messages
            messages.success(request, 'Atajos actualizados correctamente.')
            return redirect('inicio')
            
        except Exception as e:
            if request.content_type == 'application/json':
                return JsonResponse({'status': 'error', 'message': str(e)})
            
            from django.contrib import messages
            messages.error(request, f'Error al guardar: {str(e)}')
            return redirect('inicio')
    return redirect('inicio')


@login_required(login_url='login')
def menu_inicial(request):
    perfil = getattr(request.user, 'perfil', None)

    accesos_base = [
        {'url': 'perfil', 'titulo': 'Mi Perfil', 'descripcion': 'Actualiza tus datos y seguridad.', 'icono': 'bi-person-gear', 'color': 'primary'},
        {'url': 'notificaciones', 'titulo': 'Notificaciones', 'descripcion': 'Revisa alertas y avisos.', 'icono': 'bi-bell-fill', 'color': 'danger'},
        {'url': 'documentos_personal', 'titulo': 'Mi Boveda', 'descripcion': 'Firma y consulta documentos personales.', 'icono': 'bi-folder-check', 'color': 'success'},
        {'url': 'centro_ayuda', 'titulo': 'Centro de Ayuda', 'descripcion': 'Crea tickets o solicitudes.', 'icono': 'bi-headset', 'color': 'info'},
        {'url': 'calendario', 'titulo': 'Calendario', 'descripcion': 'Eventos y agenda corporativa.', 'icono': 'bi-calendar3', 'color': 'warning'},
        {'url': 'comunicados', 'titulo': 'Comunicados', 'descripcion': 'Novedades y anuncios internos.', 'icono': 'bi-megaphone-fill', 'color': 'secondary'},
    ]

    accesos_gestion = []
    if request.user.is_superuser or (perfil and perfil.puede_ver_gestion):
        accesos_gestion = [
            {'url': 'colaboradores', 'titulo': 'Directorio de Personal', 'descripcion': 'Gestion de fichas y altas.', 'icono': 'bi-people-fill', 'color': 'info'},
            {'url': 'asistencia', 'titulo': 'Asistencia', 'descripcion': 'Control de marcas y huellero.', 'icono': 'bi-fingerprint', 'color': 'warning'},
            {'url': 'vacaciones_admin', 'titulo': 'Vacaciones Admin', 'descripcion': 'Aprobaciones del equipo.', 'icono': 'bi-airplane-engines-fill', 'color': 'primary'},
            {'url': 'gestor_lms', 'titulo': 'Gestor LMS', 'descripcion': 'Cursos, lecciones y evaluaciones.', 'icono': 'bi-mortarboard-fill', 'color': 'dark'},
        ]

    return render(request, 'intranet/dashboard/menu_inicial.html', {
        'perfil': perfil,
        'accesos_base': accesos_base,
        'accesos_gestion': accesos_gestion,
    })

@login_required(login_url='login')
@solo_directivos
def dashboard(request):
    context = {
        'total_colaboradores': Colaborador.objects.count(), 
        'tickets_pendientes': Ticket.objects.filter(estado='PENDIENTE').count(), 
        'vacaciones_pendientes': SolicitudVacaciones.objects.filter(estado='PENDIENTE').count(), 
        'asistencias_hoy': Asistencia.objects.filter(fecha=date.today()).count()
    }
    return render(request, 'intranet/dashboard/dashboard.html', context)


@login_required(login_url='login')
@solo_directivos
def dashboard_rrhh(request):
    colaboradores = Colaborador.objects.select_related('user', 'area', 'cargo', 'negocio').all()
    asistencias_hoy_qs = Asistencia.objects.filter(fecha=date.today()).select_related('colaborador__user', 'colaborador__area', 'colaborador__cargo')
    
    sede = request.GET.get('sede')
    if sede:
        colaboradores = colaboradores.filter(sede=sede)
        asistencias_hoy_qs = asistencias_hoy_qs.filter(colaborador__sede=sede)
        
    tickets_pendientes = Ticket.objects.filter(estado='PENDIENTE', colaborador__in=colaboradores).count()
    vacaciones_pendientes = SolicitudVacaciones.objects.filter(estado='PENDIENTE', colaborador__in=colaboradores).count()
    asistencias_hoy = asistencias_hoy_qs.count()

    atrasos_hoy = []
    sin_marca_ingreso_hoy = []
    for asistencia in asistencias_hoy_qs:
        if not asistencia.f1_ingreso:
            sin_marca_ingreso_hoy.append(asistencia)
            continue

        hora_programada = asistencia.colaborador.hora_ingreso
        if not hora_programada:
            continue

        ingreso_programado = datetime.combine(date.today(), hora_programada)
        ingreso_real = datetime.combine(date.today(), asistencia.f1_ingreso)
        if ingreso_real > ingreso_programado + timedelta(minutes=15):
            atrasos_hoy.append({
                'colaborador': asistencia.colaborador,
                'minutos': int((ingreso_real - ingreso_programado).total_seconds() // 60),
                'hora_programada': hora_programada,
                'hora_ingreso': asistencia.f1_ingreso,
            })

    return render(request, 'intranet/rrhh/dashboard_rrhh.html', {
        'total_colaboradores': colaboradores.count(),
        'colaboradores_activos': colaboradores.filter(user__is_active=True).count(),
        'sin_area': colaboradores.filter(area__isnull=True).count(),
        'sin_cargo': colaboradores.filter(cargo__isnull=True).count(),
        'tickets_pendientes': tickets_pendientes,
        'vacaciones_pendientes': vacaciones_pendientes,
        'asistencias_hoy': asistencias_hoy,
        'atrasos_hoy': atrasos_hoy[:8],
        'sin_marca_ingreso_hoy': sin_marca_ingreso_hoy[:8],
        'areas_resumen': colaboradores.values('area__nombre').annotate(total=Count('id')).order_by('-total', 'area__nombre')[:6],
        'cargos_resumen': colaboradores.values('cargo__nombre').annotate(total=Count('id')).order_by('-total', 'cargo__nombre')[:6],
        'roles_resumen': colaboradores.values('rol').annotate(total=Count('id')).order_by('-total', 'rol'),
        'ultimos_ingresos': colaboradores.exclude(fecha_ingreso__isnull=True).order_by('-fecha_ingreso')[:8],
        'sedes': Colaborador.SEDES,
        'sede_actual': sede,
    })


@login_required(login_url='login')
@solo_directivos
def exportar_directorio_rrhh(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="directorio_rrhh.csv"'

    sede = request.GET.get('sede')
    
    writer = csv.writer(response)
    writer.writerow(['Usuario', 'Nombres', 'Apellidos', 'DNI', 'Rol', 'Area', 'Cargo', 'Cartera', 'Subcartera', 'Sede', 'Horario', 'Fecha Ingreso'])

    qs = Colaborador.objects.select_related('user', 'area', 'cargo', 'negocio').order_by('user__last_name', 'user__first_name')
    if sede:
        qs = qs.filter(sede=sede)

    for perfil in qs:
        writer.writerow([
            perfil.user.username,
            perfil.user.first_name,
            perfil.user.last_name,
            perfil.dni,
            perfil.get_rol_display(),
            perfil.area.nombre if perfil.area else '',
            perfil.cargo.nombre if perfil.cargo else '',
            perfil.negocio.nombre if perfil.negocio else '',
            perfil.subcartera or '',
            perfil.get_sede_display(),
            perfil.get_tipo_horario_display(),
            perfil.fecha_ingreso.strftime('%Y-%m-%d') if perfil.fecha_ingreso else '',
        ])

    return response


@login_required(login_url='login')
@solo_supervisores
def dashboard_supervisor(request):
    perfil = getattr(request.user, 'perfil', None)
    equipo_qs = Colaborador.objects.select_related('user', 'area', 'cargo', 'negocio').all()

    es_directivo = perfil and perfil.rol in ['GERENCIA', 'ADMINISTRATIVO']
    negocios = None
    cartera_id = None

    if es_directivo:
        from intranet.models.rrhh_core import Negocio
        negocios = Negocio.objects.filter(activo=True).order_by('nombre')
        cartera_id = request.GET.get('cartera')
        if cartera_id:
            equipo_qs = equipo_qs.filter(negocio_id=cartera_id)
    else:
        # Lógica original para supervisores puros
        if perfil and perfil.area_id:
            equipo_qs = equipo_qs.filter(area_id=perfil.area_id)
        elif perfil and perfil.cargo_id:
            equipo_qs = equipo_qs.filter(cargo_id=perfil.cargo_id)
        elif perfil and perfil.negocio_id:
            equipo_qs = equipo_qs.filter(negocio_id=perfil.negocio_id)
        else:
            equipo_qs = equipo_qs.none()

    tickets_equipo = Ticket.objects.filter(colaborador__in=equipo_qs).select_related('colaborador__user', 'colaborador__cargo').order_by('-fecha_registro')
    vacaciones_equipo = SolicitudVacaciones.objects.filter(colaborador__in=equipo_qs).select_related('colaborador__user', 'colaborador__cargo').order_by('-fecha_solicitud')
    asistencias_hoy_qs = Asistencia.objects.filter(colaborador__in=equipo_qs, fecha=date.today()).select_related('colaborador__user', 'colaborador__area', 'colaborador__cargo')

    from intranet.models.lms import MatriculaCurso
    cursos_equipo = MatriculaCurso.objects.filter(colaborador__in=equipo_qs)
    cursos_completados = cursos_equipo.filter(estado='COMPLETADO').count()
    cursos_pendientes = cursos_equipo.exclude(estado='COMPLETADO').count()

    atrasos_equipo = []
    sin_marca_equipo = []
    for asistencia in asistencias_hoy_qs:
        if not asistencia.f1_ingreso:
            sin_marca_equipo.append(asistencia)
            continue
        if asistencia.colaborador.hora_ingreso:
            hora_programada = datetime.combine(date.today(), asistencia.colaborador.hora_ingreso)
            hora_real = datetime.combine(date.today(), asistencia.f1_ingreso)
            if hora_real > hora_programada + timedelta(minutes=15):
                atrasos_equipo.append(asistencia)

    return render(request, 'intranet/rrhh/dashboard_supervisor.html', {
        'perfil': perfil,
        'es_directivo': es_directivo,
        'negocios': negocios,
        'cartera_id': int(cartera_id) if cartera_id else None,
        'equipo_total': equipo_qs.count(),
        'equipo_activo': equipo_qs.filter(user__is_active=True).count(),
        'tickets_pendientes': tickets_equipo.filter(estado='PENDIENTE').count(),
        'vacaciones_pendientes': vacaciones_equipo.filter(estado='PENDIENTE').count(),
        'asistencias_hoy': asistencias_hoy_qs.count(),
        'cursos_completados': cursos_completados,
        'cursos_pendientes': cursos_pendientes,
        'atrasos_equipo': atrasos_equipo[:8],
        'sin_marca_equipo': sin_marca_equipo[:8],
        'equipo_qs': equipo_qs.order_by('user__last_name', 'user__first_name')[:10],
        'tickets_recientes': tickets_equipo[:6],
        'vacaciones_recientes': vacaciones_equipo[:6],
    })


@login_required(login_url='login')
@solo_supervisores
def exportar_equipo_supervisor(request):
    perfil = getattr(request.user, 'perfil', None)
    equipo_qs = Colaborador.objects.select_related('user', 'area', 'cargo', 'negocio').all()

    if perfil and perfil.area_id:
        equipo_qs = equipo_qs.filter(area_id=perfil.area_id)
    elif perfil and perfil.cargo_id:
        equipo_qs = equipo_qs.filter(cargo_id=perfil.cargo_id)
    else:
        equipo_qs = equipo_qs.none()

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="equipo_supervisor.csv"'
    writer = csv.writer(response)
    writer.writerow(['Usuario', 'Nombre', 'DNI', 'Area', 'Cargo', 'Cartera', 'Subcartera', 'Rol'])
    for miembro in equipo_qs:
        writer.writerow([
            miembro.user.username,
            f'{miembro.user.first_name} {miembro.user.last_name}'.strip(),
            miembro.dni,
            miembro.area.nombre if miembro.area else '',
            miembro.cargo.nombre if miembro.cargo else '',
            miembro.negocio.nombre if miembro.negocio else '',
            miembro.subcartera or '',
            miembro.get_rol_display(),
        ])
    return response


@login_required(login_url='login')
@solo_directivos
def perfil_admin(request):
    busqueda = (request.GET.get('q') or '').strip()
    colaborador_id = (request.GET.get('colaborador') or '').strip()

    colaboradores = Colaborador.objects.select_related('user', 'area', 'cargo', 'negocio').all().order_by('user__last_name', 'user__first_name')
    if busqueda:
        colaboradores = colaboradores.filter(
            Q(user__first_name__icontains=busqueda) |
            Q(user__last_name__icontains=busqueda) |
            Q(user__username__icontains=busqueda) |
            Q(dni__icontains=busqueda)
        )

    seleccionado = None
    if colaborador_id:
        seleccionado = colaboradores.filter(pk=colaborador_id).first()
    if not seleccionado:
        seleccionado = colaboradores.first()

    if seleccionado:
        asistencias = Asistencia.objects.filter(colaborador=seleccionado).order_by('-fecha')
        tickets = Ticket.objects.filter(colaborador=seleccionado).select_related('revisado_por').order_by('-fecha_registro')
        vacaciones = SolicitudVacaciones.objects.filter(colaborador=seleccionado).select_related('revisado_por').order_by('-fecha_solicitud')
        documentos_personales = DocumentoPersonal.objects.filter(colaborador=seleccionado).select_related('emitido_por').order_by('-fecha_entrega')
        documentos_generados = DocumentoGenerado.objects.filter(colaborador=seleccionado.user).select_related('plantilla_origen').order_by('-fecha_emision')
        matriculas = MatriculaCurso.objects.filter(colaborador=seleccionado).select_related('curso').order_by('-id')
        respuestas_encuesta = RespuestaEncuesta.objects.filter(colaborador=seleccionado).select_related('pregunta__encuesta').order_by('-fecha_respuesta')
        mensajes = MensajeInterno.objects.filter(Q(remitente=seleccionado) | Q(destinatario=seleccionado)).select_related('remitente__user', 'destinatario__user').order_by('-fecha_envio')
        onboarding = CandidatoOnboarding.objects.filter(colaborador=seleccionado).first()
        eventos_proximos = EventoCalendario.objects.filter(fecha_inicio__date__gte=date.today()).order_by('fecha_inicio')
    else:
        asistencias = Ticket.objects.none()
        tickets = Ticket.objects.none()
        vacaciones = SolicitudVacaciones.objects.none()
        documentos_personales = DocumentoPersonal.objects.none()
        documentos_generados = DocumentoGenerado.objects.none()
        matriculas = MatriculaCurso.objects.none()
        respuestas_encuesta = RespuestaEncuesta.objects.none()
        mensajes = MensajeInterno.objects.none()
        onboarding = None
        eventos_proximos = EventoCalendario.objects.none()

    return render(request, 'intranet/rrhh/perfil_admin.html', {
        'colaboradores': colaboradores[:30],
        'seleccionado': seleccionado,
        'asistencias': asistencias[:10],
        'tickets': tickets[:8],
        'vacaciones': vacaciones[:8],
        'documentos_personales': documentos_personales[:8],
        'documentos_generados': documentos_generados[:8],
        'matriculas': matriculas[:8],
        'respuestas_encuesta': respuestas_encuesta[:8],
        'mensajes': mensajes[:8],
        'onboarding': onboarding,
        'eventos_proximos': eventos_proximos[:6],
        'busqueda': busqueda,
    })


@login_required(login_url='login')
def notificaciones(request):
    lista_notificaciones = request.user.notificaciones.all().order_by('-creada_en')[:60]
    return render(request, 'intranet/comunicacion/notificaciones.html', {
        'lista_notificaciones': lista_notificaciones,
    })


@login_required(login_url='login')
def leer_notificacion(request, pk):
    notificacion = get_object_or_404(request.user.notificaciones, pk=pk)
    if not notificacion.leida:
        notificacion.leida = True
        notificacion.save(update_fields=['leida'])

    if notificacion.url_destino:
        return redirect(notificacion.url_destino)
    return redirect('notificaciones')


from django.utils.http import url_has_allowed_host_and_scheme

@login_required(login_url='login')
def marcar_todas_leidas(request):
    request.user.notificaciones.filter(leida=False).update(leida=True)
    referer = request.META.get('HTTP_REFERER', '')
    if not url_has_allowed_host_and_scheme(referer, allowed_hosts={request.get_host()}):
        referer = 'inicio'
    return redirect(referer)

from django.http import JsonResponse

@login_required(login_url='login')
def notificaciones_push_ajax(request):
    try:
        # Get unread notifications
        nuevas = request.user.notificaciones.filter(leida=False).order_by('-id')[:3]
        data = []
        for n in nuevas:
            data.append({
                'id': n.id,
                'titulo': n.titulo,
                'detalle': n.detalle,
                'url': n.url_destino if n.url_destino else '/notificaciones/'
            })
        return JsonResponse({'notificaciones': data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)