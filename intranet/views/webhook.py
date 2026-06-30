import os
import json
import hmac
import hashlib
import re
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from intranet.models import CandidatoOnboarding  

WEBHOOK_API_KEY = os.environ.get('WEBHOOK_API_KEY')

def verify_webhook_signature(payload, signature):
    """Verifica la firma HMAC del webhook (seguridad extra)"""
    if not WEBHOOK_API_KEY:
        return False
    
    expected_signature = hmac.new(
        WEBHOOK_API_KEY.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)

def get_webhook_api_key(request, payload):
    return (
        request.headers.get('X-API-Key', '')
        or request.headers.get('Authorization', '').removeprefix('Bearer ').strip()
        or str(payload.get('api_key', '')).strip()
    )


def limpiar_dni(valor):
    return ''.join(ch for ch in str(valor or '') if ch.isdigit())[:8]


def limpiar_texto(valor):
    return ' '.join(str(valor or '').strip().split())


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def recibir_matriz_excel(request):
    # Soporte para CORS preflight
    if request.method == 'OPTIONS':
        response = JsonResponse({'status': 'ok'})
        response['Access-Control-Allow-Origin'] = os.environ.get('ALLOWED_ORIGIN', 'https://tu-dominio.com')
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response
    
    try:
        # Leer el cuerpo sin parsear aún (necesario para verificar firma)
        raw_body = request.body
        body = json.loads(raw_body)
        
        # Validar API Key
        api_key_recibida = get_webhook_api_key(request, body)
        
        if not api_key_recibida or not WEBHOOK_API_KEY or not hmac.compare_digest(api_key_recibida, WEBHOOK_API_KEY):
            return JsonResponse(
                {"error": "Acceso denegado."},
                status=403
            )
        
        # Validar datos
        lote = body.get('data', [])
        
        if not isinstance(lote, list) or len(lote) == 0:
            return JsonResponse(
                {"error": "Datos inválidos o vacíos"},
                status=400
            )
        
        # Limitar a 500 registros por solicitud
        lote = lote[:500]
        
        candidatos_creados = 0
        errores = 0
        
        for item in lote:
            try:
                dni = limpiar_dni(item.get('documento', ''))
                if not dni:
                    errores += 1
                    continue
                
                obj, created = CandidatoOnboarding.objects.update_or_create(
                    dni=dni,
                    defaults={
                        'nombres': limpiar_texto(item.get('nombres') or item.get('nombre', ''))[:100],
                        'apellidos': limpiar_texto(item.get('apellidos', ''))[:100],
                        'telefono': limpiar_texto(item.get('telefono', ''))[:15] or None,
                        'puesto_esperado': limpiar_texto(item.get('puesto_esperado', 'ASESOR'))[:100] or 'ASESOR',
                        'estado': 'EN_PROCESO',
                    }
                )
                if created:
                    candidatos_creados += 1
            except Exception:
                errores += 1
                continue
        
        return JsonResponse({
            "mensaje": "Lote procesado con éxito",
            "nuevos_registros": candidatos_creados,
            "errores": errores
        }, status=200)
    
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)
    except Exception:
        # No expongas detalles
        return JsonResponse({"error": "Error del servidor"}, status=500)