import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from intranet.models import CandidatoReclutamiento

# Llave maestra
API_SECRET_KEY = "RJ_Secreto_2026_Aut"

@csrf_exempt
def webhook_receptor(request):
    # Definimos los encabezados CORS como una función reutilizable
    def build_response(data, status=200):
        response = JsonResponse(data, status=status)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response

    # 1. Manejo de peticiones OPTIONS (El pre-flight de Excel/Navegador)
    if request.method == 'OPTIONS':
        return build_response({'status': 'ok'})

    # 2. Manejo de peticiones POST
    if request.method == 'POST':
        try:
            datos = json.loads(request.body)
            
            # Verificación de seguridad
            if datos.get('api_key') != API_SECRET_KEY:
                return build_response({'error': 'Acceso denegado. Llave incorrecta.'}, status=403)
            
            origen = datos.get('origen')
            
            # --- RECEPCIÓN DE BARRIDO TOTAL (EXCEL) ---
            if origen in ['excel_reclutamiento', 'excel_barrido_total']:
                lista_candidatos = datos.get('data', [])
                
                count = 0
                for item in lista_candidatos:
                    # Usamos update_or_create para evitar duplicados por DNI
                    CandidatoReclutamiento.objects.update_or_create(
                        documento=item.get('documento'),
                        defaults={
                            'nombre': item.get('nombre', ''),
                            'telefono': item.get('telefono', ''),
                            'estado_candidato': item.get('estado_candidato', ''),
                            'sede': item.get('sede', '')
                        }
                    )
                    count += 1
                
                print(f"🔄 [DB] Sincronización exitosa: {count} registros.")
                return build_response({'status': 'Sincronización exitosa', 'procesados': count})

            # --- OTRAS RECEPCIONES ---
            elif origen == 'meta_ads_reclutamiento':
                print(f"✅ [API] Nuevo lead: {datos.get('nombre_candidato')}")
                return build_response({'status': 'Candidato registrado'})
                
            elif origen == 'tv_recaudacion':
                print(f"✅ [API] Recaudación: S/ {datos.get('monto_cobrado')}")
                return build_response({'status': 'TV notificada'})

            else:
                return build_response({'error': 'Origen desconocido'}, status=400)

        except json.JSONDecodeError:
            return build_response({'error': 'JSON inválido'}, status=400)
        except Exception as e:
            return build_response({'error': str(e)}, status=500)
            
    return build_response({'error': 'Método no permitido. Usa POST.'}, status=405)