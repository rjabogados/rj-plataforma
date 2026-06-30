from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from intranet.models.rrhh_core import Colaborador
from intranet.models.comunicacion import FelicitacionCumpleaños, Reconocimiento
from datetime import date
from django.db.models import Count

@login_required(login_url='login')
def muro_celebraciones(request):
    hoy = date.today()
    # Cumpleañeros del mes (o semana)
    # Por simplicidad, filtramos por mes de nacimiento
    cumpleañeros = Colaborador.objects.filter(
        fecha_nacimiento__month=hoy.month,
        user__is_active=True
    ).order_by('fecha_nacimiento__day')

    # Filtrar notas para el cumpleañero actual
    notas_publicas = FelicitacionCumpleaños.objects.filter(privado=False).order_by('-fecha_envio')[:50]

    if request.method == 'POST':
        destinatario_id = request.POST.get('destinatario_id')
        mensaje = request.POST.get('mensaje')
        es_privado = request.POST.get('privado') == 'on'
        
        destinatario = get_object_or_404(Colaborador, id=destinatario_id)
        
        FelicitacionCumpleaños.objects.create(
            remitente=request.user.perfil,
            destinatario=destinatario,
            mensaje=mensaje,
            privado=es_privado
        )
        messages.success(request, f"¡Le has dejado una linda felicitación a {destinatario.user.first_name}!")
        return redirect('muro_celebraciones')

    es_su_cumple = False
    if request.user.perfil.fecha_nacimiento:
        if request.user.perfil.fecha_nacimiento.day == hoy.day and request.user.perfil.fecha_nacimiento.month == hoy.month:
            es_su_cumple = True

    context = {
        'cumpleañeros': cumpleañeros,
        'notas': notas_publicas,
        'hoy': hoy,
        'es_su_cumple': es_su_cumple
    }
    return render(request, 'intranet/cultura/muro_cumpleanos.html', context)


@login_required(login_url='login')
def muro_kudos(request):
    # Ranking de los que más reconocimientos han recibido
    top_reconocidos = Colaborador.objects.annotate(
        total_kudos=Count('reconocimientos_recibidos')
    ).filter(total_kudos__gt=0).order_by('-total_kudos')[:10]

    feed_kudos = Reconocimiento.objects.all().order_by('-fecha')[:50]
    
    colaboradores = Colaborador.objects.filter(user__is_active=True).exclude(id=request.user.perfil.id)

    if request.method == 'POST':
        receptor_id = request.POST.get('receptor_id')
        tipo = request.POST.get('tipo')
        mensaje = request.POST.get('mensaje')
        
        receptor = get_object_or_404(Colaborador, id=receptor_id)
        
        Reconocimiento.objects.create(
            emisor=request.user.perfil,
            receptor=receptor,
            tipo=tipo,
            mensaje=mensaje
        )
        messages.success(request, f"¡Le has dado un Kudo a {receptor.user.first_name}! Sigue fomentando el buen clima.")
        return redirect('muro_kudos')

    context = {
        'top_reconocidos': top_reconocidos,
        'feed_kudos': feed_kudos,
        'colaboradores': colaboradores,
        'tipos_medalla': Reconocimiento.TIPOS_MEDALLA
    }
    return render(request, 'intranet/cultura/muro_kudos.html', context)
