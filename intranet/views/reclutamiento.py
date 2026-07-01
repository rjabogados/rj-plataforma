import json
from django.http import JsonResponse
from django.shortcuts import render
from django.db.models import Count, Q
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from intranet.models import CandidatoReclutamiento , HistorialEstado, RegistroContacto
from django.views.decorators.http import require_http_methods
from django.utils.dateparse import parse_date
import re


def _limpiar_texto(valor):
    return ' '.join(str(valor or '').strip().split())


def _limpiar_documento(valor):
    return ''.join(ch for ch in str(valor or '') if ch.isalnum())[:20]


def _limpiar_telefono(valor):
    return ''.join(ch for ch in str(valor or '') if ch.isdigit() or ch == '+')[:20]


def _normalizar_estado(valor):
    texto = _limpiar_texto(valor).lower()
    mapa = {
        'nuevo': 'Nuevo',
        'pendiente': 'Pendiente',
        'entrevista': 'Entrevista agendada',
        'entrevista agendada': 'Entrevista agendada',
        'apto': 'Apto',
        'no apto': 'No apto',
        'no interesado': 'No interesados',
        'no interesados': 'No interesados',
        'contratado': 'Contratado',
    }
    return mapa.get(texto, _limpiar_texto(valor)[:50] or 'Nuevo')


def _serializar_historial_estado(candidato):
    historial = []

    for item in candidato.historial_estados.all().order_by('-fecha_cambio')[:12]:
        historial.append({
            'id': item.id,
            'tipo': 'estado',
            'titulo': f"{item.estado_anterior or 'Sin estado'} → {item.estado_nuevo or 'Sin estado'}",
            'detalle': 'Actualización de estado del candidato',
            'fecha': item.fecha_cambio.strftime('%d/%m/%Y %H:%M'),
        })

    for item in candidato.contactos.all().order_by('-fecha_contacto')[:12]:
        historial.append({
            'id': item.id,
            'tipo': 'contacto',
            'titulo': f"{item.tipo} - {item.asesor}",
            'detalle': item.detalle or '',
            'fecha': item.fecha_contacto.strftime('%d/%m/%Y %H:%M'),
        })

    historial.sort(key=lambda item: item['fecha'], reverse=True)
    return historial[:20]


def _partes_estructura(valor):
    texto = _limpiar_texto(valor)
    if not texto:
        return []
    return [parte.strip() for parte in re.split(r'[\|/;,:>-]+', texto) if parte and parte.strip()]


def _resolver_estructura_desde_texto(texto_combinado):
    partes = _partes_estructura(texto_combinado)
    negocio = None
    area = None
    cargo = None
    subcartera = None

    from intranet.models.rrhh_core import Negocio, Area, Cargo

    negocios = list(Negocio.objects.all().order_by('nombre'))
    areas = list(Area.objects.filter(activa=True).order_by('nombre'))
    cargos = list(Cargo.objects.filter(activa=True).select_related('area').order_by('area__nombre', 'nombre'))

    for parte in partes:
        limpio = parte.casefold()
        if not negocio:
            negocio = next((n for n in negocios if n.nombre.casefold() in limpio or limpio in n.nombre.casefold()), None)
            if negocio:
                continue
        if not area:
            area = next((a for a in areas if a.nombre.casefold() in limpio or limpio in a.nombre.casefold()), None)
            if area:
                continue
        if not cargo:
            cargo = next((c for c in cargos if c.nombre.casefold() in limpio or limpio in c.nombre.casefold()), None)
            if cargo:
                continue
        if not subcartera and len(parte) >= 3:
            subcartera = _limpiar_texto(parte)

    return negocio, area, cargo, subcartera


def usuario_puede_reclutamiento(user):
    if user.is_superuser:
        return True
    perfil = getattr(user, 'perfil', None)
    return bool(perfil and perfil.rol in ['ADMINISTRATIVO', 'RRHH', 'GERENCIA'])


def respuesta_no_autorizado():
    return JsonResponse({'success': False, 'error': 'No autorizado'}, status=403)

from intranet.views.utils import solo_directivos

@login_required(login_url='login')
@solo_directivos
def lista_candidatos(request):
    # Obtener todos los candidatos ordenados por los más recientes
    candidatos = CandidatoReclutamiento.objects.all().order_by('-fecha_registro')
    
    # Capturar parámetros de búsqueda y filtrado
    busqueda = request.GET.get('q', '').strip()
    sede_filtro = request.GET.get('sede', '').strip()
    
    # Aplicar filtros dinámicos si existen
    if busqueda:
        candidatos = candidatos.filter(
            Q(nombre__icontains=busqueda) |
            Q(documento__icontains=busqueda) |
            Q(telefono__icontains=busqueda) |
            Q(observaciones__icontains=busqueda)
        )
    
    if sede_filtro:
        candidatos = candidatos.filter(sede=sede_filtro)
        
    # Obtener la lista de sedes únicas para el menú desplegable del buscador
    sedes_disponibles = CandidatoReclutamiento.objects.exclude(sede__isnull=True).exclude(sede='').values_list('sede', flat=True).distinct().order_by('sede')

    context = {
        'candidatos': candidatos,
        'busqueda': busqueda,
        'sede_filtro': sede_filtro,
        'sedes_disponibles': sedes_disponibles,
    }
    return render(request, 'intranet/reclutamiento/lista_candidatos.html', context)

@login_required(login_url='login')
def dashboard_reclutamiento(request):
    return render(request, 'intranet/reclutamiento/dashboard_reclutamiento.html')

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
        if not usuario_puede_reclutamiento(request.user):
            return respuesta_no_autorizado()
        
        candidato = CandidatoReclutamiento.objects.get(id=candidato_id)
        candidato.estado_candidato = _normalizar_estado(nuevo_estado)
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
        if not usuario_puede_reclutamiento(request.user):
            return respuesta_no_autorizado()
        
        # Validar ID
        try:
            candidato_id = int(candidato_id)
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'ID inválido'}, status=400)
        
        candidato = CandidatoReclutamiento.objects.prefetch_related('historial_estados', 'contactos').get(id=candidato_id)
        
        data = {
            'success': True,
            'id': candidato.id,
            'nombre': candidato.nombre or '',
            'documento': candidato.documento or '',
            'telefono': candidato.telefono or '',
            'estado': candidato.estado_candidato or '',
            'sede': getattr(candidato, 'sede', 'No Asignado'),
            'canal': getattr(candidato, 'canal', 'No Asignado'),
            'observaciones': getattr(candidato, 'observaciones', '') or '',
            'historial': _serializar_historial_estado(candidato),
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
        if not usuario_puede_reclutamiento(request.user):
            return respuesta_no_autorizado()
        
        candidato_id = data.get('id')
        if not candidato_id:
            return JsonResponse({'success': False, 'error': 'ID requerido'}, status=400)
        
        candidato = CandidatoReclutamiento.objects.get(id=candidato_id)
        
        # Capturar estado anterior
        estado_viejo = candidato.estado_candidato
        
        # Actualizar con validación
        candidato.nombre = _limpiar_texto(data.get('nombre', candidato.nombre)) or candidato.nombre
        candidato.documento = _limpiar_documento(data.get('documento', candidato.documento)) or candidato.documento
        candidato.telefono = _limpiar_telefono(data.get('telefono', candidato.telefono)) or candidato.telefono
        candidato.observaciones = _limpiar_texto(data.get('observaciones', candidato.observaciones or '')) or candidato.observaciones
        
        estado_nuevo = _normalizar_estado(data.get('estado', estado_viejo))
        if estado_nuevo:
            candidato.estado_candidato = estado_nuevo
        
        candidato.sede = _limpiar_texto(data.get('sede', 'No Asignado')) or 'No Asignado'
        candidato.canal = _limpiar_texto(data.get('canal', 'Por Definir')) or 'Por Definir'

        if candidato.documento:
            duplicado = CandidatoReclutamiento.objects.exclude(id=candidato.id).filter(documento=candidato.documento).first()
            if duplicado:
                if len(_limpiar_texto(candidato.nombre)) > len(_limpiar_texto(duplicado.nombre or '')):
                    duplicado.nombre = candidato.nombre
                if len(_limpiar_telefono(candidato.telefono)) > len(_limpiar_telefono(duplicado.telefono or '')):
                    duplicado.telefono = candidato.telefono
                duplicado.estado_candidato = candidato.estado_candidato
                duplicado.sede = candidato.sede
                duplicado.canal = candidato.canal
                duplicado.save()
                candidato.delete()
                return JsonResponse({'success': True, 'mensaje': 'Registro consolidado con un duplicado existente', 'estado': candidato.estado_candidato})
        
        candidato.save()
        
        # Registrar cambio de estado
        if estado_viejo != candidato.estado_candidato:
            HistorialEstado.objects.create(
                candidato=candidato,
                estado_anterior=estado_viejo,
                estado_nuevo=candidato.estado_candidato
            )
        
        return JsonResponse({'success': True, 'mensaje': 'Actualizado correctamente', 'estado': candidato.estado_candidato})
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'Error al procesar'}, status=500)


@login_required(login_url='login')
@require_http_methods(["POST"])
def registrar_contacto_ajax(request):
    try:
        if not usuario_puede_reclutamiento(request.user):
            return respuesta_no_autorizado()

        data = json.loads(request.body)
        candidato_id = data.get('id')
        asesor = _limpiar_texto(data.get('asesor'))
        tipo = _limpiar_texto(data.get('tipo'))
        detalle = _limpiar_texto(data.get('detalle'))

        if not candidato_id or not asesor or not tipo or not detalle:
            return JsonResponse({'success': False, 'error': 'Datos incompletos'}, status=400)

        if tipo not in dict(RegistroContacto.TIPOS_CONTACTO):
            return JsonResponse({'success': False, 'error': 'Tipo de contacto inválido'}, status=400)

        candidato = CandidatoReclutamiento.objects.get(id=candidato_id)
        RegistroContacto.objects.create(
            candidato=candidato,
            asesor=asesor[:100],
            tipo=tipo,
            detalle=detalle,
        )

        return JsonResponse({
            'success': True,
            'mensaje': 'Comunicación registrada',
            'historial': _serializar_historial_estado(candidato),
        })
    except CandidatoReclutamiento.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Candidato no encontrado'}, status=404)
    except Exception:
        return JsonResponse({'success': False, 'error': 'Error al procesar'}, status=500)
        
@login_required(login_url='login')
@require_http_methods(["POST"])
def descartar_candidato_ajax(request):
    try:
        if not usuario_puede_reclutamiento(request.user):
            return respuesta_no_autorizado()
        
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
        
@login_required(login_url='login')
@require_http_methods(["POST"])
def eliminar_historial_ajax(request):
    try:
        if not usuario_puede_reclutamiento(request.user):
            return respuesta_no_autorizado()
            
        data = json.loads(request.body)
        registro_id = data.get('id')
        tipo = data.get('tipo')
        candidato_id = data.get('candidato_id')
        
        if not registro_id or not tipo or not candidato_id:
            return JsonResponse({'success': False, 'error': 'Datos incompletos'}, status=400)
            
        candidato = CandidatoReclutamiento.objects.get(id=candidato_id)
        
        if tipo == 'contacto':
            RegistroContacto.objects.filter(id=registro_id, candidato=candidato).delete()
        elif tipo == 'estado':
            HistorialEstado.objects.filter(id=registro_id, candidato=candidato).delete()
            
        return JsonResponse({
            'success': True,
            'mensaje': 'Registro eliminado',
            'historial': _serializar_historial_estado(candidato),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'Error al procesar'}, status=500)
        
@login_required(login_url='login')
@require_http_methods(["GET"])
def metricas_dashboard_ajax(request):
    """Devuelve los datos procesados para los gráficos del dashboard"""
    if not usuario_puede_reclutamiento(request.user):
        return respuesta_no_autorizado()

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
    data_sede = list(candidatos.exclude(sede__isnull=True).exclude(sede='').values('sede').annotate(total=Count('id')).order_by('-total', 'sede'))
    
    # ¿Cuántos por Estado del Embudo?
    data_estado = list(candidatos.values('estado_candidato').annotate(total=Count('id')).order_by('-total', 'estado_candidato'))

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

import csv
from django.http import HttpResponse

@login_required
def exportar_candidatos_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="Base_Reclutamiento.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['ID_Matriz', 'Nombre_Completo', 'Documento', 'Telefono', 'Estado', 'Sede', 'Canal', 'Fecha_Registro'])
    
    candidatos = CandidatoReclutamiento.objects.all().order_by('-fecha_registro')
    for c in candidatos:
        writer.writerow([
            f"M-{c.id:05d}",
            c.nombre,
            c.documento,
            c.telefono,
            c.estado_candidato,
            c.sede,
            c.canal,
            c.fecha_registro.strftime('%Y-%m-%d %H:%M') if c.fecha_registro else ''
        ])
        
    return response
