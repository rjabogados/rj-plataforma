from datetime import datetime
import mimetypes
import os
from urllib.parse import quote
from django.http import FileResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.db.models import Q

# Importamos los modelos y las herramientas de permisos compartidas
from intranet.models import Ticket, SolicitudVacaciones, Area, Cargo, Negocio
from .utils import solo_directivos

MAX_TICKET_ADJUNTO_SIZE = 10 * 1024 * 1024
TICKET_ADJUNTOS_PERMITIDOS = {'.pdf', '.jpg', '.jpeg', '.png', '.webp', '.doc', '.docx'}


def ticket_adjunto_valido(adjunto):
    if not adjunto:
        return True
    extension = os.path.splitext(adjunto.name)[1].lower()
    return extension in TICKET_ADJUNTOS_PERMITIDOS and adjunto.size <= MAX_TICKET_ADJUNTO_SIZE


def build_inline_file_response(field_file):
    if not field_file or not field_file.name:
        raise Http404('Archivo no disponible')

    storage = field_file.storage
    if not storage.exists(field_file.name):
        raise Http404('Archivo no disponible')

    filename = os.path.basename(field_file.name)
    content_type, _ = mimetypes.guess_type(filename)
    response = FileResponse(storage.open(field_file.name, 'rb'), content_type=content_type or 'application/octet-stream')
    response['Content-Disposition'] = f"inline; filename*=UTF-8''{quote(filename)}"
    return response


# ==========================================
# UTILIDADES COMPARTIDAS (DRY)
# ==========================================
def filtrar_bandeja_admin(queryset, perfil_actual, request):
    """Aplica filtros de permisos (por rol) y de búsqueda (GET params) a cualquier solicitud."""
    
    # 1. Filtro por Rol (Permisos)
    if perfil_actual.rol == 'SUPERVISOR':
        # Supervisor ve PENDIENTE_N1 de su negocio
        queryset = queryset.filter(colaborador__negocio=perfil_actual.negocio, estado='PENDIENTE_N1')
    elif perfil_actual.rol == 'ADMINISTRATIVO':
        # Administrador de Sede ve PENDIENTE_N1 y PENDIENTE_N2 de su sede
        queryset = queryset.filter(colaborador__sede=perfil_actual.sede, estado__in=['PENDIENTE_N1', 'PENDIENTE_N2'])
    elif perfil_actual.rol in ['RRHH', 'GERENCIA']:
        # RRHH/Gerencia ven todo (no se filtra estado por defecto aquí para ver histórico, o pueden filtrar en la vista si desean)
        pass

    # 2. Filtros de Búsqueda (GET Params)
    q = request.GET.get('q', '').strip()
    documento = request.GET.get('documento', '').strip()
    area_id = request.GET.get('area', '').strip()
    cargo_id = request.GET.get('cargo', '').strip()
    cartera_id = request.GET.get('cartera', '').strip()
    subcartera = request.GET.get('subcartera', '').strip()

    if q:
        queryset = queryset.filter(
            Q(colaborador__user__first_name__icontains=q) |
            Q(colaborador__user__last_name__icontains=q) |
            Q(colaborador__user__username__icontains=q) |
            Q(colaborador__dni__icontains=q)
        )
    if documento:
        queryset = queryset.filter(colaborador__dni__icontains=documento)
    if area_id:
        queryset = queryset.filter(colaborador__area_id=area_id)
    if cargo_id:
        queryset = queryset.filter(colaborador__cargo_id=cargo_id)
    if cartera_id:
        queryset = queryset.filter(colaborador__negocio_id=cartera_id)
    if subcartera:
        queryset = queryset.filter(colaborador__subcartera__icontains=subcartera)

    return queryset

def crear_ticket_desde_request(request, perfil):
    adjunto = request.FILES.get('adjunto')
    if not ticket_adjunto_valido(adjunto):
        return False, 'El adjunto debe ser PDF, imagen o Word y no superar 10 MB.'
    Ticket.objects.create(
        colaborador=perfil, 
        tipo=request.POST.get('tipo'), 
        motivo=request.POST.get('motivo'), 
        adjunto_comprobante=adjunto
    )
    return True, 'Ticket enviado correctamente.'

def crear_vacaciones_desde_request(request, perfil):
    f_ini = request.POST.get('fecha_inicio')
    f_fin = request.POST.get('fecha_fin')
    if not f_ini or not f_fin:
        return False, 'Debe especificar fecha de inicio y fin.'
    try:
        fecha_inicio = datetime.strptime(f_ini, '%Y-%m-%d').date()
        fecha_fin = datetime.strptime(f_fin, '%Y-%m-%d').date()
        if fecha_fin < fecha_inicio:
            return False, 'La fecha de fin no puede ser anterior a la fecha de inicio.'
            
        dias_solicitados = (fecha_fin - fecha_inicio).days + 1
        
        # Validacion de saldo
        if hasattr(perfil, 'saldo_vacaciones'):
            saldo = perfil.saldo_vacaciones
            if dias_solicitados > saldo.dias_disponibles:
                return False, f'No tienes suficientes días disponibles. Estás solicitando {dias_solicitados} días, pero solo tienes {saldo.dias_disponibles} disponibles.'
                
        SolicitudVacaciones.objects.create(
            colaborador=perfil, 
            fecha_inicio=fecha_inicio, 
            fecha_fin=fecha_fin
        )
        return True, 'Solicitud de vacaciones enviada correctamente.'
    except ValueError:
        return False, 'Formato de fecha inválido.'


# ==========================================
# GESTIÓN DE TICKETS E INCIDENCIAS
# ==========================================
@login_required(login_url='login')
def tickets(request):
    perfil = getattr(request.user, 'perfil', None)
    
    if request.method == 'POST' and 'crear_ticket' in request.POST and perfil:
        exito, msg = crear_ticket_desde_request(request, perfil)
        if exito:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
        return redirect('tickets')
        
    lista_tickets = Ticket.objects.filter(colaborador=perfil).order_by('-fecha_registro') if perfil else []
    return render(request, 'intranet/tickets/tickets_personal.html', {'tickets': lista_tickets})

@login_required(login_url='login')
def tickets_admin(request):
    perfil_actual = getattr(request.user, 'perfil', None)
    if not perfil_actual or not (perfil_actual.es_supervisor or perfil_actual.es_directivo):
        messages.error(request, 'No tienes permisos para acceder a esta bandeja.')
        return redirect('dashboard')
        
    qs = Ticket.objects.select_related('colaborador__user', 'colaborador__area', 'colaborador__cargo', 'colaborador__negocio').order_by('-fecha_registro')
    lista_tickets = filtrar_bandeja_admin(qs, perfil_actual, request)

    return render(request, 'intranet/tickets/tickets_admin.html', {
        'tickets': lista_tickets,
        'areas': Area.objects.filter(activa=True).order_by('nombre'),
        'cargos': Cargo.objects.filter(activa=True).select_related('area').order_by('nombre'),
        'negocios': Negocio.objects.all().order_by('nombre'),
        'perfil_actual': perfil_actual
    })

@login_required(login_url='login')
@require_http_methods(["POST"])
def revisar_ticket(request, pk, estado):
    ticket = get_object_or_404(Ticket, pk=pk)
    perfil_actual = getattr(request.user, 'perfil', None)
    
    if not perfil_actual:
        return redirect('tickets_admin')
        
    if estado not in ('APROBADO', 'RECHAZADO'):
        messages.error(request, 'Estado no válido.')
        return redirect('tickets_admin')
        
    comentarios = request.POST.get('comentarios', '')
    if ticket.procesar_aprobacion(request.user, perfil_actual, estado, comentarios):
        ticket.save()
        messages.success(request, f'Ticket actualizado a estado {ticket.get_estado_display()}')
    else:
        messages.error(request, 'No tienes permisos para cambiar este estado.')
        
    return redirect('tickets_admin')


@login_required(login_url='login')
def ver_adjunto_ticket(request, pk):
    ticket = get_object_or_404(Ticket.objects.select_related('colaborador__user'), pk=pk)
    perfil = getattr(request.user, 'perfil', None)

    if not request.user.is_superuser:
        if not perfil:
            raise Http404('Archivo no disponible')
        es_propietario = ticket.colaborador_id == perfil.id
        es_directivo = perfil.rol in ['ADMINISTRATIVO', 'RRHH', 'GERENCIA']
        if not es_propietario and not es_directivo:
            raise Http404('Archivo no disponible')

    return build_inline_file_response(ticket.adjunto_comprobante)


# ==========================================
# GESTIÓN DE VACACIONES
# ==========================================
@login_required(login_url='login')
def vacaciones(request):
    perfil = getattr(request.user, 'perfil', None)
    
    if request.method == 'POST' and 'solicitar_vac' in request.POST and perfil:
        exito, msg = crear_vacaciones_desde_request(request, perfil)
        if exito:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
        return redirect('vacaciones')
        
    lista_solicitudes = SolicitudVacaciones.objects.filter(colaborador=perfil).order_by('-fecha_solicitud') if perfil else []
    saldo = getattr(perfil, 'saldo_vacaciones', None) if perfil else None
    
    return render(request, 'intranet/solicitudes/vacaciones_personal.html', {
        'solicitudes': lista_solicitudes,
        'saldo': saldo
    })

@login_required(login_url='login')
def vacaciones_admin(request):
    perfil_actual = getattr(request.user, 'perfil', None)
    if not perfil_actual or not (perfil_actual.es_supervisor or perfil_actual.es_directivo):
        messages.error(request, 'No tienes permisos para acceder a esta bandeja.')
        return redirect('dashboard')
        
    qs = SolicitudVacaciones.objects.select_related('colaborador__user', 'colaborador__area', 'colaborador__cargo', 'colaborador__negocio').order_by('-fecha_solicitud')
    solicitudes_qs = filtrar_bandeja_admin(qs, perfil_actual, request)

    if request.method == 'POST' and 'gestionar_vac' in request.POST:
        sol_id = request.POST.get('solicitud_id')
        solicitud = get_object_or_404(SolicitudVacaciones, id=sol_id)
        nuevo_estado = request.POST.get('estado')
        comentarios = request.POST.get('comentarios', '')
        
        if solicitud.procesar_aprobacion(request.user, perfil_actual, nuevo_estado, comentarios):
            solicitud.save()
            messages.success(request, f'Solicitud de vacaciones actualizada a estado {solicitud.get_estado_display()}.')
        else:
            messages.error(request, 'No tienes permisos para cambiar este estado.')
            
        return redirect('vacaciones_admin')
        
    return render(request, 'intranet/admin/vacaciones_admin.html', {
        'solicitudes': solicitudes_qs,
        'areas': Area.objects.filter(activa=True).order_by('nombre'),
        'cargos': Cargo.objects.filter(activa=True).select_related('area').order_by('nombre'),
        'negocios': Negocio.objects.all().order_by('nombre'),
        'perfil_actual': perfil_actual
    })

@login_required(login_url='login')
@solo_directivos
@require_http_methods(["POST"])
def eliminar_vacaciones(request, pk): 
    get_object_or_404(SolicitudVacaciones, pk=pk).delete()
    messages.success(request, 'Solicitud eliminada correctamente.')
    return redirect('vacaciones_admin')


# ==========================================
# CENTRO DE AYUDA (MESA DE AYUDA UNIFICADA)
# ==========================================
@login_required(login_url='login')
def centro_ayuda(request):
    perfil = getattr(request.user, 'perfil', None)
    
    if request.method == 'POST' and perfil:
        if 'crear_ticket' in request.POST:
            exito, msg = crear_ticket_desde_request(request, perfil)
            if exito:
                messages.success(request, msg)
            else:
                messages.error(request, msg)
            return redirect('centro_ayuda')
            
        elif 'solicitar_vac' in request.POST:
            exito, msg = crear_vacaciones_desde_request(request, perfil)
            if exito:
                messages.success(request, msg)
            else:
                messages.error(request, msg)
            return redirect('centro_ayuda')

    lista_tickets = Ticket.objects.filter(colaborador=perfil).order_by('-fecha_registro') if perfil else []
    lista_vacaciones = SolicitudVacaciones.objects.filter(colaborador=perfil).order_by('-fecha_solicitud') if perfil else []
    
    return render(request, 'intranet/solicitudes/centro_ayuda.html', {
        'tickets': lista_tickets,
        'solicitudes_vacaciones': lista_vacaciones,
        'page_title': 'Centro de Solicitudes'
    })

# ==========================================
# CALENDARIO DE AUSENCIAS
# ==========================================
@login_required(login_url='login')
def calendario_ausencias(request):
    perfil = getattr(request.user, 'perfil', None)
    if not perfil or not (perfil.es_supervisor or perfil.es_directivo):
        messages.error(request, 'No tienes permisos para ver el calendario de ausencias.')
        return redirect('dashboard')
        
    # Filtrar solo vacaciones aprobadas
    qs_vacaciones = SolicitudVacaciones.objects.filter(estado='APROBADO')
    qs_vacaciones = filtrar_bandeja_admin(qs_vacaciones, perfil, request)
    
    # Filtrar tickets medicos/ausencias aprobados
    # Asumimos que TARDANZA, INASISTENCIA, MEDICO son ausencias. Si TARDANZA no lo es, filtramos.
    qs_tickets = Ticket.objects.filter(estado='APROBADO', tipo__in=['INASISTENCIA', 'MEDICO'])
    qs_tickets = filtrar_bandeja_admin(qs_tickets, perfil, request)
    
    eventos = []
    
    for vac in qs_vacaciones:
        if vac.fecha_inicio and vac.fecha_fin:
            eventos.append({
                'title': f"Vacaciones: {vac.colaborador.user.get_full_name()}",
                'start': vac.fecha_inicio.strftime('%Y-%m-%d'),
                'end': (vac.fecha_fin).strftime('%Y-%m-%d'), # Para FullCalendar a veces hay q sumar 1 dia al end, lo manejamos en js
                'color': '#0dcaf0', # info color
                'tipo': 'vacaciones',
                'colaborador': vac.colaborador.user.get_full_name()
            })
            
    for t in qs_tickets:
        eventos.append({
            'title': f"Ausencia: {t.colaborador.user.get_full_name()} ({t.get_tipo_display()})",
            'start': t.fecha_registro.strftime('%Y-%m-%d'),
            'color': '#dc3545', # danger color
            'tipo': 'ticket',
            'colaborador': t.colaborador.user.get_full_name()
        })

    return render(request, 'intranet/solicitudes/calendario_ausencias.html', {
        'eventos': eventos
    })