import json
from django.http import JsonResponse
from django.shortcuts import render
from django.db.models import Count
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from intranet.models import CandidatoReclutamiento , HistorialEstado, RegistroContacto
from django.views.decorators.http import require_http_methods
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
    return render(request, 'intranet/reclutamiento/lista_candidatos.html', context)

@login_required(login_url='login')
@require_http_methods(["POST"])
def actualizar_estado_ajax(request):
    try:
        data = json.loads(request.body)
        candidato_id = data.get('id')
        nuevo_estado = data.get('estado')
        
        # Validación de datos
        if not candidato_id or not nuevo_estado:
            return JsonResponse({'success': False, 'error': 'Datos incompletos'}, status=400)
        
        # Validar que el usuario es directivo
        perfil = getattr(request.user, 'perfil', None)
        if not perfil or perfil.rol not in ['ADMINISTRATIVO', 'RRHH', 'GERENCIA']:
            return JsonResponse({'success': False, 'error': 'No autorizado'}, status=403)
        
        candidato = CandidatoReclutamiento.objects.get(id=candidato_id)
        candidato.estado_candidato = nuevo_estado
        candidato.save()
        
        return JsonResponse({'success': True, 'mensaje': 'Estado actualizado'}, status=200)
    except CandidatoReclutamiento.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Candidato no encontrado'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    except Exception as e:
        # ✅ No expongas detalles del error
        return JsonResponse({'success': False, 'error': 'Error al procesar'}, status=500)
        
@login_required(login_url='login')
@require_http_methods(["GET"])
def obtener_candidato_ajax(request, candidato_id):
    try:
        # Verificar permisos
        perfil = getattr(request.user, 'perfil', None)
        if not perfil or perfil.rol not in ['ADMINISTRATIVO', 'RRHH', 'GERENCIA']:
            return JsonResponse({'success': False, 'error': 'No autorizado'}, status=403)
        
        # Validar ID
        try:
            candidato_id = int(candidato_id)
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'ID inválido'}, status=400)
        
        candidato = CandidatoReclutamiento.objects.get(id=candidato_id)
        
        data = {
            'success': True,
            'id': candidato.id,
            'nombre': candidato.nombre or '',
            'documento': candidato.documento or '',
            'telefono': candidato.telefono or '',
            'estado': candidato.estado_candidato or '',
            'sede': getattr(candidato, 'sede', 'No Asignado'),
            'canal': getattr(candidato, 'canal', 'No Asignado')
        }
        return JsonResponse(data)
    except CandidatoReclutamiento.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Candidato no encontrado'}, status=404)
    except Exception:
        return JsonResponse({'success': False, 'error': 'Error al procesar'}, status=500)

@login_required(login_url='login')
@require_http_methods(["POST"])
def actualizar_candidato_ajax(request):
    try:
        data = json.loads(request.body)
        
        # Validar permiso
        perfil = getattr(request.user, 'perfil', None)
        if not perfil or perfil.rol not in ['ADMINISTRATIVO', 'RRHH', 'GERENCIA']:
            return JsonResponse({'success': False, 'error': 'No autorizado'}, status=403)
        
        candidato_id = data.get('id')
        if not candidato_id:
            return JsonResponse({'success': False, 'error': 'ID requerido'}, status=400)
        
        candidato = CandidatoReclutamiento.objects.get(id=candidato_id)
        
        # Capturar estado anterior
        estado_viejo = candidato.estado_candidato
        
        # Actualizar con validación
        candidato.nombre = data.get('nombre', candidato.nombre)
        candidato.documento = data.get('documento', candidato.documento)
        candidato.telefono = data.get('telefono', candidato.telefono)
        
        estado_nuevo = data.get('estado', estado_viejo)
        if estado_nuevo:
            candidato.estado_candidato = estado_nuevo
        
        candidato.sede = data.get('sede', 'No Asignado')
        candidato.canal = data.get('canal', 'Meta Ads')
        
        candidato.save()
        
        # Registrar cambio de estado
        if estado_viejo != candidato.estado_candidato:
            HistorialEstado.objects.create(
                candidato=candidato,
                estado_anterior=estado_viejo,
                estado_nuevo=candidato.estado_candidato
            )
        
        return JsonResponse({'success': True, 'mensaje': 'Actualizado correctamente'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'Error al procesar'}, status=500)
        
@login_required(login_url='login')
@require_http_methods(["POST"])
def descartar_candidato_ajax(request):
    try:
        perfil = getattr(request.user, 'perfil', None)
        if not perfil or perfil.rol not in ['ADMINISTRATIVO', 'RRHH', 'GERENCIA']:
            return JsonResponse({'success': False, 'error': 'No autorizado'}, status=403)
        
        data = json.loads(request.body)
        candidato_id = data.get('id')
        
        if not candidato_id:
            return JsonResponse({'success': False, 'error': 'ID requerido'}, status=400)
        
        candidato = CandidatoReclutamiento.objects.get(id=candidato_id)
        estado_viejo = candidato.estado_candidato
        
        candidato.estado_candidato = 'No interesados'
        candidato.save()
        
        HistorialEstado.objects.create(
            candidato=candidato,
            estado_anterior=estado_viejo,
            estado_nuevo='No interesados'
        )
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'Error al procesar'}, status=500)
        
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