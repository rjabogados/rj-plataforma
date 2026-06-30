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
# GESTIÓN DE TICKETS E INCIDENCIAS
# ==========================================
@login_required(login_url='login')
def tickets(request):
    """Vista para que el colaborador cree y vea sus propios tickets."""
    perfil = getattr(request.user, 'perfil', None)
    
    if request.method == 'POST' and 'crear_ticket' in request.POST and perfil:
        adjunto = request.FILES.get('adjunto')
        if not ticket_adjunto_valido(adjunto):
            messages.error(request, 'El adjunto debe ser PDF, imagen o Word y no superar 10 MB.')
            return redirect('tickets')
        Ticket.objects.create(
            colaborador=perfil, 
            tipo=request.POST.get('tipo'), 
            motivo=request.POST.get('motivo'), 
            adjunto_comprobante=adjunto
        )
        messages.success(request, 'Ticket enviado correctamente.')
        return redirect('tickets')
        
    lista_tickets = Ticket.objects.filter(colaborador=perfil).order_by('-fecha_registro') if perfil else []
    return render(request, 'intranet/tickets/tickets_personal.html', {'tickets': lista_tickets})

@login_required(login_url='login')
@solo_directivos
def tickets_admin(request):
    """Panel gerencial para ver todos los tickets de la empresa."""
    lista_tickets = Ticket.objects.select_related('colaborador__user', 'colaborador__area', 'colaborador__cargo', 'colaborador__negocio', 'revisado_por').all().order_by('-fecha_registro')

    q = request.GET.get('q', '').strip()
    documento = request.GET.get('documento', '').strip()
    area_id = request.GET.get('area', '').strip()
    cargo_id = request.GET.get('cargo', '').strip()
    cartera_id = request.GET.get('cartera', '').strip()
    subcartera = request.GET.get('subcartera', '').strip()

    if q:
        lista_tickets = lista_tickets.filter(
            Q(colaborador__user__first_name__icontains=q) |
            Q(colaborador__user__last_name__icontains=q) |
            Q(colaborador__user__username__icontains=q) |
            Q(colaborador__dni__icontains=q)
        )

    if documento:
        lista_tickets = lista_tickets.filter(colaborador__dni__icontains=documento)
    if area_id:
        lista_tickets = lista_tickets.filter(colaborador__area_id=area_id)
    if cargo_id:
        lista_tickets = lista_tickets.filter(colaborador__cargo_id=cargo_id)
    if cartera_id:
        lista_tickets = lista_tickets.filter(colaborador__negocio_id=cartera_id)
    if subcartera:
        lista_tickets = lista_tickets.filter(colaborador__subcartera__icontains=subcartera)

    return render(request, 'intranet/tickets/tickets_admin.html', {
        'tickets': lista_tickets,
        'areas': Area.objects.filter(activa=True).order_by('nombre'),
        'cargos': Cargo.objects.filter(activa=True).select_related('area').order_by('nombre'),
        'negocios': Negocio.objects.all().order_by('nombre'),
    })

@login_required(login_url='login')
@solo_directivos
@require_http_methods(["POST"])
def revisar_ticket(request, pk, estado):
    """Acción rápida para aprobar o rechazar un ticket."""
    ticket = get_object_or_404(Ticket, pk=pk)
    if estado in ['APROBADO', 'RECHAZADO']:
        ticket.estado = estado
        ticket.revisado_por = request.user
        ticket.save()
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
    """Vista para que el colaborador solicite y vea el estado de sus vacaciones."""
    perfil = getattr(request.user, 'perfil', None)
    
    if request.method == 'POST' and 'solicitar_vac' in request.POST and perfil:
        f_ini, f_fin = request.POST.get('fecha_inicio'), request.POST.get('fecha_fin')
        if f_ini and f_fin:
            fecha_inicio = datetime.strptime(f_ini, '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(f_fin, '%Y-%m-%d').date()
            if fecha_fin < fecha_inicio:
                messages.error(request, 'La fecha de fin no puede ser anterior a la fecha de inicio.')
                return redirect('vacaciones')
            SolicitudVacaciones.objects.create(
                colaborador=perfil, 
                fecha_inicio=fecha_inicio, 
                fecha_fin=fecha_fin
            )
            messages.success(request, 'Solicitud de vacaciones enviada correctamente.')
        return redirect('vacaciones')
        
    lista_solicitudes = SolicitudVacaciones.objects.filter(colaborador=perfil).order_by('-fecha_solicitud') if perfil else []
    return render(request, 'intranet/solicitudes/vacaciones_personal.html', {'solicitudes': lista_solicitudes})

@login_required(login_url='login')
@solo_directivos
def vacaciones_admin(request):
    """Panel gerencial para gestionar y comentar las solicitudes de vacaciones."""
    solicitudes_qs = SolicitudVacaciones.objects.select_related('colaborador__user', 'colaborador__area', 'colaborador__cargo', 'colaborador__negocio', 'revisado_por').all().order_by('-fecha_solicitud')

    q = request.GET.get('q', '').strip()
    documento = request.GET.get('documento', '').strip()
    area_id = request.GET.get('area', '').strip()
    cargo_id = request.GET.get('cargo', '').strip()
    cartera_id = request.GET.get('cartera', '').strip()
    subcartera = request.GET.get('subcartera', '').strip()

    if q:
        solicitudes_qs = solicitudes_qs.filter(
            Q(colaborador__user__first_name__icontains=q) |
            Q(colaborador__user__last_name__icontains=q) |
            Q(colaborador__user__username__icontains=q) |
            Q(colaborador__dni__icontains=q)
        )
    if documento:
        solicitudes_qs = solicitudes_qs.filter(colaborador__dni__icontains=documento)
    if area_id:
        solicitudes_qs = solicitudes_qs.filter(colaborador__area_id=area_id)
    if cargo_id:
        solicitudes_qs = solicitudes_qs.filter(colaborador__cargo_id=cargo_id)
    if cartera_id:
        solicitudes_qs = solicitudes_qs.filter(colaborador__negocio_id=cartera_id)
    if subcartera:
        solicitudes_qs = solicitudes_qs.filter(colaborador__subcartera__icontains=subcartera)

    if request.method == 'POST' and 'gestionar_vac' in request.POST:
        sol_id = request.POST.get('solicitud_id')
        solicitud = get_object_or_404(SolicitudVacaciones, id=sol_id)
        
        nuevo_estado = request.POST.get('estado')
        if nuevo_estado not in ['APROBADO', 'RECHAZADO']:
            messages.error(request, 'Estado de resolución inválido.')
            return redirect('vacaciones_admin')

        solicitud.estado = nuevo_estado
        solicitud.comentarios_rrhh = request.POST.get('comentarios')
        solicitud.revisado_por = request.user
        solicitud.save()
        messages.success(request, 'Solicitud actualizada correctamente.')
        return redirect('vacaciones_admin')
        
    return render(request, 'intranet/admin/vacaciones_admin.html', {
        'solicitudes': solicitudes_qs,
        'areas': Area.objects.filter(activa=True).order_by('nombre'),
        'cargos': Cargo.objects.filter(activa=True).select_related('area').order_by('nombre'),
        'negocios': Negocio.objects.all().order_by('nombre'),
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
    """Portal unificado para creación y seguimiento de tickets y vacaciones."""
    perfil = getattr(request.user, 'perfil', None)
    
    if request.method == 'POST' and perfil:
        if 'crear_ticket' in request.POST:
            adjunto = request.FILES.get('adjunto')
            if not ticket_adjunto_valido(adjunto):
                messages.error(request, 'El adjunto debe ser PDF, imagen o Word y no superar 10 MB.')
                return redirect('centro_ayuda')
            Ticket.objects.create(
                colaborador=perfil, 
                tipo=request.POST.get('tipo'), 
                motivo=request.POST.get('motivo'), 
                adjunto_comprobante=adjunto
            )
            messages.success(request, 'Ticket enviado correctamente.')
            return redirect('centro_ayuda')
            
        elif 'solicitar_vac' in request.POST:
            f_ini, f_fin = request.POST.get('fecha_inicio'), request.POST.get('fecha_fin')
            if f_ini and f_fin:
                try:
                    fecha_inicio = datetime.strptime(f_ini, '%Y-%m-%d').date()
                    fecha_fin = datetime.strptime(f_fin, '%Y-%m-%d').date()
                    if fecha_fin < fecha_inicio:
                        messages.error(request, 'La fecha de fin no puede ser anterior a la fecha de inicio.')
                        return redirect('centro_ayuda')
                    SolicitudVacaciones.objects.create(
                        colaborador=perfil, 
                        fecha_inicio=fecha_inicio, 
                        fecha_fin=fecha_fin
                    )
                    messages.success(request, 'Solicitud de vacaciones enviada correctamente.')
                except ValueError:
                    messages.error(request, 'Formato de fecha inválido.')
            return redirect('centro_ayuda')

    lista_tickets = Ticket.objects.filter(colaborador=perfil).order_by('-fecha_registro') if perfil else []
    lista_vacaciones = SolicitudVacaciones.objects.filter(colaborador=perfil).order_by('-fecha_solicitud') if perfil else []
    
    return render(request, 'intranet/solicitudes/centro_ayuda.html', {
        'tickets': lista_tickets,
        'solicitudes_vacaciones': lista_vacaciones,
        'page_title': 'Centro de Solicitudes'
    })