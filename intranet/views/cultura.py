from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from intranet.models.rrhh_core import Colaborador
from intranet.models.comunicacion import FelicitacionCumpleaños, Reconocimiento
from datetime import date
from django.db.models import Count
from django.core.exceptions import ObjectDoesNotExist

MESES_ES = {
    1: 'Enero',
    2: 'Febrero',
    3: 'Marzo',
    4: 'Abril',
    5: 'Mayo',
    6: 'Junio',
    7: 'Julio',
    8: 'Agosto',
    9: 'Setiembre',
    10: 'Octubre',
    11: 'Noviembre',
    12: 'Diciembre',
}

@login_required(login_url='login')
def muro_celebraciones(request):
    hoy = date.today()
    try:
        perfil = request.user.perfil
        tiene_perfil = True
    except ObjectDoesNotExist:
        perfil = None
        tiene_perfil = False

    # Cumpleañeros del mes (o semana)
    # Por simplicidad, filtramos por mes de nacimiento
    cumpleaneros = list(Colaborador.objects.filter(
        fecha_nacimiento__month=hoy.month,
        user__is_active=True
    ).order_by('fecha_nacimiento__day'))

    for persona in cumpleaneros:
        persona.es_hoy = bool(
            persona.fecha_nacimiento
            and persona.fecha_nacimiento.day == hoy.day
            and persona.fecha_nacimiento.month == hoy.month
        )
        persona.mes_es = MESES_ES.get(persona.fecha_nacimiento.month, '') if persona.fecha_nacimiento else ''

    # Filtrar notas para el cumpleañero actual
    notas_publicas = FelicitacionCumpleaños.objects.filter(privado=False).order_by('-fecha_envio')[:50]

    if request.method == 'POST':
        if not tiene_perfil:
            messages.error(request, "Tu usuario no tiene un perfil asignado para realizar esta acción.")
            return redirect('muro_celebraciones')

        destinatario_id = request.POST.get('destinatario_id')
        mensaje = request.POST.get('mensaje')
        es_privado = request.POST.get('privado') == 'on'
        
        destinatario = get_object_or_404(Colaborador, id=destinatario_id)
        
        if not destinatario.permitir_mensajes_cumpleanos:
            messages.error(request, f"{destinatario.user.first_name} ha desactivado los mensajes de cumpleaños en su perfil.")
            return redirect('muro_celebraciones')

        FelicitacionCumpleaños.objects.create(
            remitente=request.user.perfil,
            destinatario=destinatario,
            mensaje=mensaje,
            privado=es_privado
        )
        messages.success(request, f"¡Le has dejado una linda felicitación a {destinatario.user.first_name}!")
        return redirect('muro_celebraciones')

    es_su_cumple = False
    if tiene_perfil and perfil.fecha_nacimiento:
        if perfil.fecha_nacimiento.day == hoy.day and perfil.fecha_nacimiento.month == hoy.month:
            es_su_cumple = True

    context = {
        'cumpleaneros': cumpleaneros,
        'notas': notas_publicas,
        'hoy': hoy,
        'es_su_cumple': es_su_cumple,
        'mes_actual_es': MESES_ES.get(hoy.month, ''),
    }
    return render(request, 'intranet/cultura/muro_cumpleanos.html', context)


@login_required(login_url='login')
def muro_kudos(request):
    try:
        perfil = request.user.perfil
        tiene_perfil = True
    except ObjectDoesNotExist:
        perfil = None
        tiene_perfil = False
        
    MEDALLAS_SUPERVISOR_KEYS = ['ESTRELLA', 'LIDERAZGO', 'SOLUCIONADOR']
    
    es_supervisor = False
    if tiene_perfil:
        es_supervisor = perfil.es_supervisor or perfil.es_directivo

    q_cartera = None
    if tiene_perfil and not perfil.es_directivo:
        if perfil.subcartera:
            subcarteras = [s.strip() for s in perfil.subcartera.split(',') if s.strip()]
            q_cartera = Q()
            for sc in subcarteras:
                q_cartera |= Q(subcartera__icontains=sc)
        elif perfil.negocio_id or perfil.carteras_secundarias.exists():
            q_cartera = Q(negocio_id=perfil.negocio_id) if perfil.negocio_id else Q()
            for car_sec in perfil.carteras_secundarias.all():
                q_cartera |= Q(negocio_id=car_sec.id)

    # Ranking de los que más reconocimientos han recibido
    qs_ranking = Colaborador.objects.all()
    if q_cartera:
        qs_ranking = qs_ranking.filter(q_cartera)
        
    top_reconocidos = qs_ranking.annotate(
        total_kudos=Count('reconocimientos_recibidos')
    ).filter(total_kudos__gt=0).order_by('-total_kudos')[:10]

    # Ranking específico: El más Migajero
    from django.db.models import Q
    top_migajeros = qs_ranking.annotate(
        total_migajas=Count('reconocimientos_recibidos', filter=Q(reconocimientos_recibidos__tipo='MIGAJERO'))
    ).filter(total_migajas__gt=0).order_by('-total_migajas')[:5]

    qs_feed = Reconocimiento.objects.all()
    if q_cartera:
        qs_feed = qs_feed.filter(Q(receptor__in=qs_ranking) | Q(emisor__in=qs_ranking))
    feed_kudos = qs_feed.order_by('-fecha')[:50]
    
    colaboradores = Colaborador.objects.filter(user__is_active=True)
    if q_cartera:
        colaboradores = colaboradores.filter(q_cartera)
        
    if tiene_perfil:
        colaboradores = colaboradores.exclude(id=perfil.id)

    if request.method == 'POST':
        if not tiene_perfil:
            messages.error(request, "Tu usuario no tiene un perfil asignado para realizar esta acción.")
            return redirect('muro_kudos')

        receptor_id = request.POST.get('receptor_id')
        tipo = request.POST.get('tipo')
        mensaje = request.POST.get('mensaje')
        
        receptor = get_object_or_404(Colaborador, id=receptor_id)
        
        if tipo in MEDALLAS_SUPERVISOR_KEYS and not es_supervisor:
            messages.error(request, "Esta medalla solo puede ser otorgada por un supervisor a discreción.")
            return redirect('muro_kudos')
            
        # ✅ Verificar que no haya enviado un Kudo al mismo receptor hoy
        if Reconocimiento.objects.filter(emisor=perfil, receptor=receptor, fecha__date=date.today()).exists():
            messages.warning(request, f"Ya le enviaste un Kudo a {receptor.user.first_name} el día de hoy.")
            return redirect('muro_kudos')
            
        # Determinar puntos basados en el tipo
        puntos_map = {
            'ESTRELLA': 50,
            'COMPAÑERO': 20,
            'INNOVADOR': 40,
            'LIDERAZGO': 30,
            'SOLUCIONADOR': 25,
            'MIGAJERO': 10,
        }
        puntos = puntos_map.get(tipo, 10)
        
        Reconocimiento.objects.create(
            emisor=perfil,
            receptor=receptor,
            tipo=tipo,
            mensaje=mensaje,
            puntos_otorgados=puntos
        )
        
        # Sumar puntos al receptor
        receptor.puntos_acumulados += puntos
        receptor.puntos_disponibles += puntos
        receptor.save()
        
        messages.success(request, f"¡Le has dado un Kudo a {receptor.user.first_name} y sumó {puntos} pts!")
        return redirect('muro_kudos')

    context = {
        'top_reconocidos': top_reconocidos,
        'top_migajeros': top_migajeros,
        'feed_kudos': feed_kudos,
        'colaboradores': colaboradores,
        'tipos_medalla': Reconocimiento.TIPOS_MEDALLA,
        'es_supervisor': es_supervisor,
        'mis_puntos': perfil.puntos_disponibles if tiene_perfil else 0
    }
    return render(request, 'intranet/cultura/muro_kudos.html', context)


from intranet.models.comunicacion import CatalogoPremio, CanjePremio
from intranet.views.utils import solo_directivos

@login_required(login_url='login')
def catalogo_premios(request):
    try:
        perfil = request.user.perfil
        tiene_perfil = True
    except ObjectDoesNotExist:
        perfil = None
        tiene_perfil = False
        
    premios = CatalogoPremio.objects.filter(activo=True).order_by('costo_puntos')
    mis_canjes = CanjePremio.objects.filter(colaborador=perfil).order_by('-fecha_solicitud') if tiene_perfil else []
    
    if request.method == 'POST':
        if not tiene_perfil:
            messages.error(request, "Tu usuario no tiene un perfil asignado para realizar canjes.")
            return redirect('catalogo_premios')
            
        premio_id = request.POST.get('premio_id')
        premio = get_object_or_404(CatalogoPremio, id=premio_id)
        
        if premio.stock <= 0:
            messages.error(request, "Este premio está agotado.")
        elif perfil.puntos_disponibles < premio.costo_puntos:
            messages.error(request, "No tienes suficientes puntos para este premio.")
        else:
            # Descontar puntos y crear canje
            perfil.puntos_disponibles -= premio.costo_puntos
            perfil.save()
            premio.stock -= 1
            premio.save()
            
            CanjePremio.objects.create(
                colaborador=perfil,
                premio=premio,
                estado='PENDIENTE'
            )
            messages.success(request, f"¡Has canjeado {premio.nombre}! RRHH te contactará para la entrega.")
        return redirect('catalogo_premios')
        
    context = {
        'premios': premios,
        'mis_canjes': mis_canjes,
        'puntos_disponibles': perfil.puntos_disponibles if tiene_perfil else 0
    }
    return render(request, 'intranet/cultura/catalogo_premios.html', context)

@login_required(login_url='login')
@solo_directivos
def admin_gamificacion(request):
    canjes_pendientes = CanjePremio.objects.filter(estado='PENDIENTE').order_by('fecha_solicitud')
    canjes_historico = CanjePremio.objects.exclude(estado='PENDIENTE').order_by('-fecha_resolucion')[:50]
    colaboradores = Colaborador.objects.filter(user__is_active=True).order_by('-puntos_acumulados')
    premios = CatalogoPremio.objects.all().order_by('-activo', 'costo_puntos')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'resolver_canje':
            canje_id = request.POST.get('canje_id')
            nuevo_estado = request.POST.get('estado')
            canje = get_object_or_404(CanjePremio, id=canje_id)
            
            if nuevo_estado == 'RECHAZADO':
                # Devolver puntos y stock
                canje.colaborador.puntos_disponibles += canje.premio.costo_puntos
                canje.colaborador.save()
                canje.premio.stock += 1
                canje.premio.save()
            
            canje.estado = nuevo_estado
            from django.utils import timezone
            canje.fecha_resolucion = timezone.now()
            canje.save()
            messages.success(request, f"Canje marcado como {nuevo_estado}.")
            
        elif action == 'dar_puntos':
            colab_id = request.POST.get('colaborador_id')
            puntos = int(request.POST.get('puntos', 0))
            motivo = request.POST.get('motivo', 'Bono manual RRHH')
            
            if puntos > 0:
                colab = get_object_or_404(Colaborador, id=colab_id)
                colab.puntos_acumulados += puntos
                colab.puntos_disponibles += puntos
                colab.save()
                messages.success(request, f"Se han otorgado {puntos} pts a {colab.user.first_name}.")
                
        elif action == 'crear_premio':
            nombre = request.POST.get('nombre')
            descripcion = request.POST.get('descripcion')
            costo = int(request.POST.get('costo_puntos', 100))
            stock = int(request.POST.get('stock', 10))
            imagen = request.FILES.get('imagen')
            
            CatalogoPremio.objects.create(
                nombre=nombre,
                descripcion=descripcion,
                costo_puntos=costo,
                stock=stock,
                imagen=imagen
            )
            messages.success(request, f"¡Premio '{nombre}' creado exitosamente en el catálogo!")
            
        elif action == 'toggle_premio':
            premio_id = request.POST.get('premio_id')
            premio = get_object_or_404(CatalogoPremio, id=premio_id)
            premio.activo = not premio.activo
            premio.save()
            estado_txt = "activado" if premio.activo else "desactivado"
            messages.success(request, f"Premio '{premio.nombre}' ha sido {estado_txt}.")

        return redirect('admin_gamificacion')

    context = {
        'canjes_pendientes': canjes_pendientes,
        'canjes_historico': canjes_historico,
        'colaboradores': colaboradores,
        'premios': premios
    }
    return render(request, 'intranet/cultura/admin_gamificacion.html', context)
