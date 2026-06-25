import json
import PyPDF2
import google.generativeai as genai
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required

# IMPORTACIÓN CORRECTA: Apuntando a tus modelos exactos
from ..models.lms import CursoInduccion, EvaluacionCurso, PreguntaEvaluacion, OpcionRespuesta 

# Configurar la llave de Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)

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
                messages.error(request, "No se pudo extraer texto del PDF (podría ser una imagen escaneada).")
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

            # 3. LLAMADA A GEMINI (Buscador exclusivo de modelos Gemini)
            modelo_elegido = None
            modelos_disponibles = []
            
            for m in genai.list_models():
                # Filtramos para que SOLO agarre modelos de la familia Gemini
                if 'generateContent' in m.supported_generation_methods and 'gemini' in m.name.lower():
                    modelos_disponibles.append(m.name)
            
            if not modelos_disponibles:
                raise Exception("Tu API Key no tiene modelos Gemini activados. Verifica tu cuenta en Google AI Studio.")
            
            # Buscamos el mejor modelo compatible con tu llave en este orden
            for preferido in ['1.5-flash', '1.0-pro', 'gemini-pro']:
                for m in modelos_disponibles:
                    if preferido in m.lower():
                        modelo_elegido = m
                        break
                if modelo_elegido:
                    break
            
            # Si no encuentra los preferidos, usa el primer Gemini que encuentre
            if not modelo_elegido:
                modelo_elegido = modelos_disponibles[0]
                
            modelo = genai.GenerativeModel(modelo_elegido)
            respuesta = modelo.generate_content(prompt)
            
            # 4. LIMPIEZA EXTREMA DEL JSON
            texto_limpio = respuesta.text
            if "```json" in texto_limpio:
                texto_limpio = texto_limpio.split("```json")[1].split("```")[0]
            elif "```" in texto_limpio:
                texto_limpio = texto_limpio.split("```")[1].split("```")[0]
            
            texto_json = texto_limpio.strip()
            datos_examen = json.loads(texto_json)

            # 5. GUARDAR EN BASE DE DATOS (CON TODOS LOS CAMPOS OBLIGATORIOS)
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

            # Si el examen ya existía, actualizamos la cantidad de preguntas a mostrar
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

            # Notificamos el éxito y qué modelo exacto nos salvó la vida
            messages.success(request, f"¡Éxito! Se crearon {len(datos_examen)} preguntas con IA usando el modelo {modelo_elegido.replace('models/', '')}.")
            return redirect('gestor_lms')

        except json.JSONDecodeError:
            messages.error(request, "La IA de Gemini se confundió al estructurar las preguntas. Por favor, intenta generar de nuevo.")
            return redirect('gestor_lms')
        except Exception as e:
            messages.error(request, f"Error al procesar: {str(e)}")
            return redirect('gestor_lms')

    return render(request, 'intranet/lms/generador_ia.html', {'curso': curso})