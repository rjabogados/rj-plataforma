import json
import PyPDF2
import google.generativeai as genai
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from ..models.lms import CursoInduccion, EvaluacionCurso, PreguntaEvaluacion, OpcionRespuesta 

genai.configure(api_key=settings.GEMINI_API_KEY)

@login_required
def generar_examen_ia(request, curso_id):
    curso = get_object_or_404(CursoInduccion, id=curso_id)

    if request.method == 'POST':
        archivo_pdf = request.FILES.get('documento_pdf')
        instrucciones = request.POST.get('instrucciones', '')
        cantidad = request.POST.get('cantidad_preguntas', '5')

        if not archivo_pdf:
            messages.error(request, "Por favor, sube un archivo PDF.")
            return redirect('gestor_lms') # <--- CORREGIDO AQUÍ

        try:
            lector_pdf = PyPDF2.PdfReader(archivo_pdf)
            texto_extraido = ""
            for pagina in lector_pdf.pages:
                texto_extraido += pagina.extract_text() + "\n"

            if not texto_extraido.strip():
                messages.error(request, "No se pudo extraer texto del PDF.")
                return redirect('gestor_lms') # <--- CORREGIDO AQUÍ

            prompt = f"""
            Eres un experto en Recursos Humanos y diseño de evaluaciones corporativas.
            Basándote EXCLUSIVAMENTE en el siguiente texto extraído de un manual de la empresa, 
            genera un examen de {cantidad} preguntas de opción múltiple.
            
            Instrucciones adicionales del administrador: {instrucciones}

            REGLA DE ORO: Tu respuesta debe ser ÚNICAMENTE un objeto JSON válido.
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

            modelo = genai.GenerativeModel('gemini-1.5-flash')
            respuesta = modelo.generate_content(prompt)
            
            texto_respuesta = respuesta.text.replace("```json", "").replace("```", "").strip()
            datos_examen = json.loads(texto_respuesta)

            evaluacion, created = EvaluacionCurso.objects.get_or_create(
                curso=curso,
                defaults={'titulo': f'Examen: {curso.titulo}'}
            )

            for item in datos_examen:
                nueva_pregunta = PreguntaEvaluacion.objects.create(
                    evaluacion=evaluacion,
                    enunciado=item['enunciado'],
                    puntos=20.00 / int(cantidad)
                )
                
                for alt in item['alternativas']:
                    OpcionRespuesta.objects.create(
                        pregunta=nueva_pregunta,
                        texto=alt['texto'],
                        es_correcta=alt['es_correcta']
                    )

            messages.success(request, f"¡Éxito! Se crearon {len(datos_examen)} preguntas con IA para el curso {curso.titulo}.")
            return redirect('gestor_lms') # <--- CORREGIDO AQUÍ

        except Exception as e:
            messages.error(request, f"Hubo un error con la IA: {str(e)}")
            return redirect('gestor_lms') # <--- CORREGIDO AQUÍ

    return render(request, 'intranet/lms/generador_ia.html', {'curso': curso})