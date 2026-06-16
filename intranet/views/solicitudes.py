from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

# Importamos los modelos y las herramientas de permisos compartidas
from intranet.models import Ticket, SolicitudVacaciones
from .utils import solo_directivos

# ==========================================
# GESTIÓN DE TICKETS E INCIDENCIAS
# ==========================================
@login_required(login_url='login')
def tickets(request):
    """Vista para que el colaborador cree y vea sus propios tickets."""
    perfil = getattr(request.user, 'perfil', None)
    
    if request.method == 'POST' and 'crear_ticket' in request.POST and perfil:
        Ticket.objects.create(
            colaborador=perfil, 
            tipo=request.POST.get('tipo'), 
            motivo=request.POST.get('motivo'), 
            adjunto_comprobante=request.FILES.get('adjunto')
        )
        return redirect('tickets')
        
    lista_tickets = Ticket.objects.filter(colaborador=perfil).order_by('-fecha_registro') if perfil else []
    return render(request, 'intranet/tickets_personal.html', {'tickets': lista_tickets})

@login_required(login_url='login')
@solo_directivos
def tickets_admin(request):
    """Panel gerencial para ver todos los tickets de la empresa."""
    lista_tickets = Ticket.objects.all().order_by('-fecha_registro')
    return render(request, 'intranet/tickets_admin.html', {'tickets': lista_tickets})

@login_required(login_url='login')
@solo_directivos
def revisar_ticket(request, pk, estado):
    """Acción rápida para aprobar o rechazar un ticket."""
    ticket = get_object_or_404(Ticket, pk=pk)
    if estado in ['APROBADO', 'RECHAZADO']:
        ticket.estado = estado
        ticket.revisado_por = request.user
        ticket.save()
    return redirect('tickets_admin')


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
            SolicitudVacaciones.objects.create(
                colaborador=perfil, 
                fecha_inicio=datetime.strptime(f_ini, '%Y-%m-%d').date(), 
                fecha_fin=datetime.strptime(f_fin, '%Y-%m-%d').date()
            )
        return redirect('vacaciones')
        
    lista_solicitudes = SolicitudVacaciones.objects.filter(colaborador=perfil).order_by('-fecha_solicitud') if perfil else []
    return render(request, 'intranet/vacaciones_personal.html', {'solicitudes': lista_solicitudes})

@login_required(login_url='login')
@solo_directivos
def vacaciones_admin(request):
    """Panel gerencial para gestionar y comentar las solicitudes de vacaciones."""
    if request.method == 'POST' and 'gestionar_vac' in request.POST:
        sol_id = request.POST.get('solicitud_id')
        solicitud = get_object_or_404(SolicitudVacaciones, id=sol_id)
        
        solicitud.estado = request.POST.get('estado')
        solicitud.comentarios_rrhh = request.POST.get('comentarios')
        solicitud.revisado_por = request.user
        solicitud.save()
        return redirect('vacaciones_admin')
        
    return render(request, 'intranet/vacaciones_admin.html', {
        'solicitudes': SolicitudVacaciones.objects.all().order_by('-fecha_solicitud')
    })

@login_required(login_url='login')
@solo_directivos
def eliminar_vacaciones(request, pk): 
    get_object_or_404(SolicitudVacaciones, pk=pk).delete()
    return redirect('vacaciones_admin')