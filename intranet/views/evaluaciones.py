from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from intranet.models.evaluaciones import Examen, PreguntaExamen, OpcionExamen, Intento, RespuestaUsuario

@login_required
def lista_examenes(request):
    # Trae todos los exámenes activos
    examenes = Examen.objects.filter(activo=True)
    
    # Busca si el usuario ya rindió alguno para mostrarle su nota
    intentos = Intento.objects.filter(usuario=request.user)
    examenes_realizados = intentos.values_list('examen_id', flat=True)

    return render(request, 'intranet/evaluaciones/lista.html', {
        'examenes': examenes,
        'intentos': intentos,
        'examenes_realizados': examenes_realizados
    })

@login_required
def rendir_examen(request, examen_id):
    # Trae el examen y sus preguntas de la base de datos
    examen = get_object_or_404(Examen, id=examen_id, activo=True)
    preguntas = examen.preguntas.all()

    if request.method == 'POST':
        # El usuario presionó "Enviar", creamos el registro de su Intento
        intento = Intento.objects.create(
            usuario=request.user,
            examen=examen,
            estado='FINALIZADO'
        )
        
        respuestas_correctas = 0
        total_preguntas = preguntas.count()

        # Recorremos cada pregunta para ver qué marcó el usuario
        for pregunta in preguntas:
            opcion_id = request.POST.get(f'pregunta_{pregunta.id}')
            if opcion_id:
                opcion = get_object_or_404(OpcionExamen, id=opcion_id)
                # Guardamos su respuesta en la base de datos para la auditoría
                RespuestaUsuario.objects.create(
                    intento=intento,
                    pregunta=pregunta,
                    opcion_seleccionada=opcion
                )
                if opcion.es_correcta:
                    respuestas_correctas += 1

        # Calculamos la nota vigesimal (sobre 20)
        score = 0
        if total_preguntas > 0:
            score = (respuestas_correctas / total_preguntas) * 20
            
        intento.score_total = score
        intento.save()

        # Le damos feedback inmediato al colaborador
        if score >= examen.nota_aprobacion:
            messages.success(request, f"¡Aprobaste! Tu calificación es {score:.2f}/20.")
        else:
            messages.error(request, f"No alcanzaste el mínimo. Tu calificación es {score:.2f}/20.")
            
        return redirect('lista_examenes')

    # Si es GET, simplemente le mostramos el formulario con las preguntas
    return render(request, 'intranet/evaluaciones/rendir.html', {
        'examen': examen,
        'preguntas': preguntas
    })