import json
import PyPDF2
import requests
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required

# IMPORTACIÓN CORRECTA: Apuntando a tus modelos exactos
from ..models.lms import CursoInduccion, EvaluacionCurso, PreguntaEvaluacion, OpcionRespuesta 

@login_required
def generar_examen_ia(request, curso_id):
    # Buscamos tu modelo real
    curso = get_object_or_404(CursoInduccion, id=curso_id)

    if request.method == 'POST':
        archivo_pdf = request.FILES.get('documento_pdf')
        instrucciones = request.POST.get('instrucciones', '')
        cantidad = request.POST.get('cantidad_preguntas', '5')
        cantidad_int = int(cantidad)

        if not archivo_pdf:
            messages.error(request, "Por favor, sube un archivo PDF.")
            return redirect('gestor_lms')

        try:
            # 1. LEER EL PDF
            lector_pdf = PyPDF2.PdfReader(archivo_pdf)
            texto_extraido = ""
            for pagina in lector_pdf.pages:
                texto_extraido += pagina.extract_text() + "\n"

            if not texto_extraido.strip():
                messages.error(request, "No se pudo extraer texto del PDF.")
                return redirect('gestor_lms')

            # 2. EL SÚPER PROMPT PARA GEMINI
            prompt = f"""
            Eres un experto en Recursos Humanos y diseño de evaluaciones corporativas.
            Basándote EXCLUSIVAMENTE en el siguiente texto extraído de un manual de la empresa, 
            genera un examen de {cantidad} preguntas de opción múltiple.
            
            Instrucciones adicionales: {instrucciones}

            REGLA DE ORO: Devuelve ÚNICAMENTE un array JSON válido. NO uses formato markdown (sin ```json). Solo el texto del array.
            Usa exactamente esta estructura:
            [
                {{
                    "enunciado": "Texto de la pregunta",
                    "alternativas": [
                        {{"texto": "Opción A", "es_correcta": true}},
                        {{"texto": "Opción B", "es_correcta": false}},
                        {{"texto": "Opción C", "es_correcta": false}},
                        {{"texto": "Opción D", "es_correcta": false}}
                    ]
                }}
            ]

            TEXTO DEL MANUAL:
            {texto_extraido[:25000]}
            """

            # 3. CONEXIÓN NATIVA ANTI-ENLACES (Totalmente fragmentada)
            api_key = str(settings.GEMINI_API_KEY).strip()
            
            # Fragmentamos la URL para evitar que el navegador la convierta en link
            parte1 = "https://"
            parte2 = "generativelanguage"
            parte3 = ".googleapis.com"
            parte4 = "/v1beta/models/gemini-1.5-flash:generateContent"
            
            # Ensamblaje seguro
            url_limpia = f"{parte1}{parte2}{parte3}{parte4}?key={api_key}"
            
            headers = {'Content-Type': 'application/json'}
            data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2}
            }
            
            respuesta_cruda = requests.post(url_limpia, headers=headers, json=data)
            
            if respuesta_cruda.status_code != 200:
                error_msg = respuesta_cruda.json().get('error', {}).get('message', 'Error desconocido de la API')
                raise Exception(f"Google rechazó la conexión directa: {error_msg}")

            respuesta_json = respuesta_cruda.json()
            texto_limpio = respuesta_json['candidates'][0]['content']['parts'][0]['text']

            # 4. LIMPIEZA EXTREMA DEL JSON
            if "```json" in texto_limpio:
                texto_limpio = texto_limpio.split("```json")[1].split("```")[0]
            elif "```" in texto_limpio:
                texto_limpio = texto_limpio.split("```")[1].split("```")[0]
            
            texto_json = texto_limpio.strip()
            datos_examen = json.loads(texto_json)

            # 5. GUARDAR EN BASE DE DATOS
            evaluacion, created = EvaluacionCurso.objects.get_or_create(
                curso=curso,
                defaults={
                    'titulo': f'Examen: {curso.titulo}',
                    'puntaje_maximo': 20,
                    'puntaje_aprobatorio': 14,
                    'tiempo_limite_minutos': 15,
                    'puntos_premio': 50,
                    'preguntas_a_mostrar': cantidad_int,
                    'orden_aleatorio': True
                }
            )

            # Si el examen ya existía, actualizamos la cantidad
            if not created:
                evaluacion.preguntas_a_mostrar = cantidad_int
                evaluacion.save()

            puntos_por_pregunta = round(20.00 / cantidad_int, 2)

            for item in datos_examen:
                nueva_pregunta = PreguntaEvaluacion.objects.create(
                    evaluacion=evaluacion,
                    enunciado=item['enunciado'],
                    puntos=puntos_por_pregunta
                )
                
                for alt in item['alternativas']:
                    OpcionRespuesta.objects.create(
                        pregunta=nueva_pregunta,
                        texto=alt['texto'],
                        es_correcta=alt['es_correcta']
                    )

            messages.success(request, f"¡Éxito! Se crearon {len(datos_examen)} preguntas con IA de forma directa y blindada.")
            return redirect('gestor_lms')

        except json.JSONDecodeError:
            messages.error(request, "La IA de Gemini se confundió al estructurar las preguntas. Por favor, intenta generar de nuevo.")
            return redirect('gestor_lms')
        except Exception as e:
            messages.error(request, f"Error al procesar: {str(e)}")
            return redirect('gestor_lms')

    return render(request, 'intranet/lms/generador_ia.html', {'curso': curso})