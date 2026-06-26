from datetime import date
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required

# Importamos los modelos desde la carpeta superior
from intranet.models import Comunicado, Colaborador, Ticket, SolicitudVacaciones, Asistencia, DocumentoGenerado
# Importamos nuestras herramientas de seguridad
from .utils import solo_directivos

def login_view(request):
    if request.method == 'POST':
        user = authenticate(request, username=request.POST.get('username'), password=request.POST.get('password'))
        if user is not None:
            login(request, user)
            return redirect('inicio')
        else:
            return render(request, 'intranet/auth/login.html', {'error': 'Usuario o contraseña incorrectos'})
    return render(request, 'intranet/auth/login.html')

@login_required
def perfil(request):
    return render(request, 'intranet/rrhh/perfil.html')

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

    # 3. Enviar las variables al HTML
    context = {
        'comunicados': comunicados,
        'total_colaboradores': total_colaboradores,
        'tickets_pendientes': tickets_pendientes,
        'mis_documentos': mis_documentos,
    }
    
    return render(request, 'intranet/dashboard/inicio.html', context)

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