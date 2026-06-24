import json
import PyPDF2
import google.generativeai as genai
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required

# IMPORTANTE: Asegúrate de importar tus modelos reales aquí. 
# Reemplaza 'app_name' por el nombre de tu aplicación (ej. 'intranet' o 'lms')
from ..models import Curso, Pregunta, Alternativa 

# Configurar la llave de Gemini que pusimos en settings.py
genai.configure(api_key=settings.GEMINI_API_KEY)

@login_required
def generar_examen_ia(request, curso_id):
    # Obtenemos el curso al que le vamos a crear el examen
    curso = get_object_or_404(Curso, id=curso_id)

    if request.method == 'POST':
        archivo_pdf = request.FILES.get('documento_pdf')
        instrucciones = request.POST.get('instrucciones', '')
        cantidad = request.POST.get('cantidad_preguntas', '5')

        if not archivo_pdf:
            messages.error(request, "Por favor, sube un archivo PDF.")
            return redirect('detalle_curso', curso_id=curso.id) # Cambia esto por tu URL real

        try:
            # 1. LEER EL PDF
            lector_pdf = PyPDF2.PdfReader(archivo_pdf)
            texto_extraido = ""
            for pagina in lector_pdf.pages:
                texto_extraido += pagina.extract_text() + "\n"

            if not texto_extraido.strip():
                messages.error(request, "No se pudo extraer texto del PDF (podría ser una imagen escaneada).")
                return redirect('detalle_curso', curso_id=curso.id)

            # 2. EL SÚPER PROMPT PARA GEMINI (Reglas estrictas)
            prompt = f"""
            Eres un experto en Recursos Humanos y diseño de evaluaciones corporativas.
            Basándote EXCLUSIVAMENTE en el siguiente texto extraído de un manual de la empresa, 
            genera un examen de {cantidad} preguntas de opción múltiple.
            
            Instrucciones adicionales del administrador: {instrucciones}

            REGLA DE ORO: Tu respuesta debe ser ÚNICAMENTE un objeto JSON válido, sin texto antes ni después, sin formato markdown (```json). 
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
            {texto_extraido[:25000]} # Limitamos un poco para no saturar si es muy inmenso
            """

            # 3. LLAMAR A GEMINI
            modelo = genai.GenerativeModel('gemini-1.5-flash')
            respuesta = modelo.generate_content(prompt)
            
            # Limpiar la respuesta por si Gemini le pone "```json" al inicio
            texto_respuesta = respuesta.text.replace("```json", "").replace("```", "").strip()
            
            # 4. CONVERTIR EL JSON EN PREGUNTAS REALES EN DJANGO
            datos_examen = json.loads(texto_respuesta)

            for item in datos_examen:
                # Crear la pregunta asociada al curso
                nueva_pregunta = Pregunta.objects.create(
                    curso=curso,
                    enunciado=item['enunciado']
                )
                # Crear sus 4 alternativas
                for alt in item['alternativas']:
                    Alternativa.objects.create(
                        pregunta=nueva_pregunta,
                        texto=alt['texto'],
                        es_correcta=alt['es_correcta']
                    )

            messages.success(request, f"¡Magia! Se crearon {len(datos_examen)} preguntas automáticamente.")
            return redirect('detalle_curso', curso_id=curso.id)

        except Exception as e:
            messages.error(request, f"Hubo un error con la IA: {str(e)}")
            return redirect('detalle_curso', curso_id=curso.id)

    # Si es GET, mostrar la pantalla de subida (que haremos en el siguiente paso)
    return render(request, 'intranet/lms/generador_ia.html', {'curso': curso})