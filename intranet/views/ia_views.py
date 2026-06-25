import json
import re
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

            REGLA DE ORO: Devuelve ÚNICAMENTE un array JSON válido. NO digas "Aquí tienes", NO uses formato markdown. Solo el array.
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

            # 3. LLAMAR A GEMINI
            modelo = genai.GenerativeModel('gemini-1.5-flash')
            respuesta = modelo.generate_content(prompt)
            
            # 4. EXTRACTOR BLINDADO DE JSON (Ignora texto basura)
            texto_limpio = respuesta.text
            match = re.search(r'\[\s*\{.*\}\s*\]', texto_limpio, re.DOTALL)
            
            if match:
                texto_json = match.group(0)
            else:
                texto_json = texto_limpio.replace("```json", "").replace("```", "").strip()
            
            datos_examen = json.loads(texto_json)

            # 5. GUARDAR EN TU BASE DE DATOS REAL
            evaluacion, created = EvaluacionCurso.objects.get_or_create(
                curso=curso,
                defaults={'titulo': f'Examen: {curso.titulo}'}
            )

            # Cálculo de puntos redondeado a 2 decimales para evitar fallos matemáticos
            puntos_por_pregunta = round(20.00 / int(cantidad), 2)

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

            messages.success(request, f"¡Éxito! Se crearon {len(datos_examen)} preguntas con IA para el curso {curso.titulo}.")
            return redirect('gestor_lms')

        except Exception as e:
            # Aquí imprimimos el error EXACTO para saber qué pasa
            messages.error(request, f"Hubo un error con la IA: {str(e)}")
            return redirect('gestor_lms')

    return render(request, 'intranet/lms/generador_ia.html', {'curso': curso})