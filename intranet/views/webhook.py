import os
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from intranet.models import CandidatoOnboarding  # Ajusta si tu modelo se llama distinto en la carpeta models

@csrf_exempt  
def recibir_matriz_excel(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            
            # El sistema busca la llave oculta en Render. Si no la encuentra, usa la anterior por defecto para no romper nada
            api_key_segura = os.environ.get('WEBHOOK_API_KEY', 'RJ_Secreto_2026_Aut')
            
            if body.get('api_key') != api_key_segura:
                return JsonResponse({"error": "Acceso denegado. Llave incorrecta."}, status=403)
            
            lote = body.get('data', [])
            candidatos_creados = 0
            
            for item in lote:
                obj, created = CandidatoOnboarding.objects.update_or_create(
                    telefono=item.get('telefono'),
                    defaults={
                        'documento': item.get('documento', ''),
                        'nombre': item.get('nombre', ''),
                        'estado_candidato': item.get('estado_candidato', ''),
                        'sede': item.get('sede', '')
                    }
                )
                if created:
                    candidatos_creados += 1
                    
            return JsonResponse({
                "mensaje": "Lote procesado con éxito", 
                "nuevos_registros": candidatos_creados
            }, status=200)
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
            
    return JsonResponse({"error": "Método no permitido. Usa POST."}, status=405)