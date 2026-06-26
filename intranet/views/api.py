import os
import json
import hmac
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from intranet.models import CandidatoReclutamiento

# Llave maestra (puede estar vacía en desarrollo para permitir migraciones)
API_SECRET_KEY = os.environ.get('API_SECRET_KEY')


def get_api_key(request, payload):
    return (
        request.headers.get('X-API-Key', '')
        or request.headers.get('Authorization', '').removeprefix('Bearer ').strip()
        or str(payload.get('api_key', '')).strip()
    )

@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def webhook_receptor(request):
    # Validar que la clave esté configurada cuando se intente usar
    if not API_SECRET_KEY:
        return JsonResponse({'error': 'API_SECRET_KEY no configurada'}, status=500)
    
    def build_response(data, status=200):
        response = JsonResponse(data, status=status)
        # CORS SEGURO: Especificar origen permitido
        allowed_origin = os.environ.get('ALLOWED_ORIGIN', 'https://tu-dominio.com')
        response["Access-Control-Allow-Origin"] = allowed_origin
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response["Access-Control-Max-Age"] = "3600"
        return response

    if request.method == 'OPTIONS':
        return build_response({'status': 'ok'})

    if request.method == 'POST':
        try:
            datos = json.loads(request.body)
            
            # Validar API Key
            api_key_recibida = get_api_key(request, datos)
            
            # Comparación segura (previene timing attacks)
            if not api_key_recibida or not hmac.compare_digest(api_key_recibida, API_SECRET_KEY):
                return build_response({'error': 'Acceso denegado.'}, status=403)
            
            origen = datos.get('origen', '').strip()
            
            if not origen:
                return build_response({'error': 'Origen debe ser especificado'}, status=400)
            
            if origen in ['excel_reclutamiento', 'excel_barrido_total']:
                lista_candidatos = datos.get('data', [])
                
                if not isinstance(lista_candidatos, list) or len(lista_candidatos) == 0:
                    return build_response({'error': 'Datos vacíos'}, status=400)
                
                # Limitar a 1000 registros por solicitud
                lista_candidatos = lista_candidatos[:1000]
                
                count = 0
                for item in lista_candidatos:
                    # Validar documento antes de crear
                    documento = str(item.get('documento', '')).strip()
                    if not documento or len(documento) > 20:
                        continue
                    
                    CandidatoReclutamiento.objects.update_or_create(
                        documento=documento,
                        defaults={
                            'nombre': str(item.get('nombre', ''))[:200],
                            'telefono': str(item.get('telefono', ''))[:20],
                            'estado_candidato': str(item.get('estado_candidato', 'Nuevo'))[:50],
                            'sede': str(item.get('sede', ''))[:100]
                        }
                    )
                    count += 1
                
                return build_response({
                    'status': 'Sincronización exitosa',
                    'procesados': count
                })
            
            elif origen == 'meta_ads_reclutamiento':
                return build_response({'status': 'Candidato registrado'})
            
            elif origen == 'tv_recaudacion':
                return build_response({'status': 'TV notificada'})
            
            else:
                return build_response({'error': 'Origen desconocido'}, status=400)

        except json.JSONDecodeError:
            return build_response({'error': 'JSON inválido'}, status=400)
        except Exception:
            # No expongas detalles del error
            return build_response({'error': 'Error del servidor'}, status=500)
    
    return build_response({'error': 'Método no permitido'}, status=405)