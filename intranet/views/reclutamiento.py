import json
from django.shortcuts import render
from django.db.models import Count
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from intranet.models import CandidatoReclutamiento , HistorialEstado, RegistroContacto
from django.utils.dateparse import parse_date

@login_required
def lista_candidatos(request):
    # Obtener todos los candidatos ordenados por los más recientes
    candidatos = CandidatoReclutamiento.objects.all().order_by('-fecha_registro')
    
    # Capturar parámetros de búsqueda y filtrado
    busqueda = request.GET.get('q', '').strip()
    sede_filtro = request.GET.get('sede', '').strip()
    
    # Aplicar filtros dinámicos si existen
    if busqueda:
        candidatos = candidatos.filter(nombre__icontains=busqueda) | candidatos.filter(documento__icontains=busqueda)
    
    if sede_filtro:
        candidatos = candidatos.filter(sede=sede_filtro)
        
    # Obtener la lista de sedes únicas para el menú desplegable del buscador
    sedes_disponibles = CandidatoReclutamiento.objects.values_list('sede', flat=True).distinct()

    context = {
        'candidatos': candidatos,
        'busqueda': busqueda,
        'sede_filtro': sede_filtro,
        'sedes_disponibles': sedes_disponibles,
    }
    return render(request, 'intranet/lista_candidatos.html', context)

@csrf_exempt 
def actualizar_estado_ajax(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            candidato_id = data.get('id')
            nuevo_estado = data.get('estado')
            
            # Buscamos al candidato y actualizamos
            candidato = CandidatoReclutamiento.objects.get(id=candidato_id)
            candidato.estado_candidato = nuevo_estado
            candidato.save()
            
            return JsonResponse({'success': True, 'mensaje': 'Estado actualizado'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
        
def obtener_candidato_ajax(request, candidato_id):
    try:
        candidato = CandidatoReclutamiento.objects.get(id=candidato_id)
        
        # Usamos getattr para evitar el error si la columna no existe en tu base de datos
        sede_segura = getattr(candidato, 'sede', 'No Asignado')
        canal_seguro = getattr(candidato, 'canal', 'No Asignado')
        
        data = {
            'success': True,
            'id': candidato.id,
            'nombre': candidato.nombre,
            'documento': candidato.documento if candidato.documento else '',
            'telefono': candidato.telefono,
            'estado': candidato.estado_candidato,
            'sede': sede_segura,
            'canal': canal_seguro
        }
        return JsonResponse(data)
    except CandidatoReclutamiento.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Candidato no encontrado'})

@csrf_exempt
def actualizar_candidato_ajax(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            candidato = CandidatoReclutamiento.objects.get(id=data.get('id'))
            
            # 1. CAPTURAMOS EL ESTADO ANTERIOR
            estado_viejo = candidato.estado_candidato
            
            # --- ESCUDO ANTI-VACÍOS PARA EL ESTADO ---
            # Si el frontend manda un estado vacío por error, mantenemos el que ya tenía.
            estado_nuevo = data.get('estado')
            if not estado_nuevo:
                estado_nuevo = estado_viejo if estado_viejo else 'Nuevo'
            
            # 2. ACTUALIZAMOS LOS DATOS BÁSICOS
            candidato.nombre = data.get('nombre', candidato.nombre)
            candidato.documento = data.get('documento', candidato.documento)
            candidato.telefono = data.get('telefono', candidato.telefono)
            candidato.estado_candidato = estado_nuevo
            
            # --- BARRERA DE SEGURIDAD PARA SEDE Y CANAL ---
            sede_recibida = data.get('sede')
            candidato.sede = sede_recibida if sede_recibida else "No Asignado"
            
            canal_recibido = data.get('canal')
            candidato.canal = canal_recibido if canal_recibido else "Meta Ads"
            
            candidato.save()
            
            # 3. CREAMOS EL HISTORIAL AUTOMÁTICAMENTE
            if estado_viejo != estado_nuevo:
                HistorialEstado.objects.create(
                    candidato=candidato,
                    estado_anterior=estado_viejo,
                    estado_nuevo=estado_nuevo
                )
                
            return JsonResponse({'success': True, 'mensaje': 'Actualizado correctamente'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
        
def descartar_candidato_ajax(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            candidato = CandidatoReclutamiento.objects.get(id=data.get('id'))
            candidato.estado_candidato = 'No interesados'
            candidato.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
        
def metricas_dashboard_ajax(request):
    """Devuelve los datos procesados para los gráficos del dashboard"""
    candidatos = CandidatoReclutamiento.objects.all()

    # 1. Filtros de Período (Fechas)
    fecha_inicio = request.GET.get('inicio')
    fecha_fin = request.GET.get('fin')

    if fecha_inicio:
        candidatos = candidatos.filter(fecha_registro__date__gte=parse_date(fecha_inicio))
    if fecha_fin:
        candidatos = candidatos.filter(fecha_registro__date__lte=parse_date(fecha_fin))

    # 2. KPIs Generales
    total_candidatos = candidatos.count()
    agendados = candidatos.filter(estado_candidato='Entrevista agendada').count()
    no_aptos = candidatos.filter(estado_candidato__in=['No apto', 'No interesados']).count()

    # 3. Agrupación de Datos para los Gráficos
    # ¿Cuántos por Sede?
    data_sede = list(candidatos.values('sede').annotate(total=Count('id')).order_by('-total'))
    
    # ¿Cuántos por Estado del Embudo?
    data_estado = list(candidatos.values('estado_candidato').annotate(total=Count('id')).order_by('-total'))

    return JsonResponse({
        'success': True,
        'kpis': {
            'total': total_candidatos,
            'agendados': agendados,
            'descartados': no_aptos
        },
        'grafico_sedes': data_sede,
        'grafico_estados': data_estado
    })