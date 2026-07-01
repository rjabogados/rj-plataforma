from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal

from intranet.models.desempeno import PeriodoEvaluacion, EvaluacionDesempeno, DetalleEvaluacion
from intranet.views.utils import solo_directivos

@login_required
@solo_directivos
def dashboard_desempeno(request):
    periodos = PeriodoEvaluacion.objects.all()
    periodo_activo = periodos.filter(activo=True).first()
    
    if not periodo_activo:
        # Si no hay activo, coger el ultimo
        periodo_activo = periodos.first()

    context = {
        'periodos': periodos,
        'periodo_activo': periodo_activo,
    }

    if periodo_activo:
        evaluaciones = EvaluacionDesempeno.objects.filter(periodo=periodo_activo)
        context['total_evaluaciones'] = evaluaciones.count()
        context['evaluadas'] = evaluaciones.filter(estado__in=['EVALUADO', 'CERRADO']).count()
        context['pendientes'] = evaluaciones.filter(estado__in=['PENDIENTE', 'AUTOEVALUADO']).count()
        
        # 9 box calculos
        # 9 box calculos
        nine_box = {
            'riesgo': 0,
            'inconsistente': 0,
            'enigma': 0,
            'efectivo': 0,
            'clave': 0,
            'alto_potencial': 0,
            'experto': 0,
            'estrella': 0,
            'lider': 0,
        }
        
        mapa_cuadrantes = {
            'Riesgo / Bajo Desempeño': 'riesgo',
            'Inconsistente': 'inconsistente',
            'Enigma / Diamante en Bruto': 'enigma',
            'Efectivo / Profesional Sólido': 'efectivo',
            'Colaborador Clave': 'clave',
            'Alto Potencial': 'alto_potencial',
            'Profesional Experto': 'experto',
            'Estrella Actual': 'estrella',
            'Futuro Líder / Superestrella': 'lider',
        }
        
        for ev in evaluaciones.filter(estado__in=['EVALUADO', 'CERRADO']):
            cuadrante = ev.cuadrante_9box
            key = mapa_cuadrantes.get(cuadrante)
            if key in nine_box:
                nine_box[key] += 1
            
        context['nb_counts'] = nine_box
        context['evaluaciones'] = evaluaciones

    return render(request, 'intranet/rrhh/desempeno/dashboard.html', context)

@login_required
def mis_evaluaciones(request):
    perfil = getattr(request.user, 'perfil', None)
    if not perfil:
        messages.info(request, 'No se encontro un perfil asociado. Te mostramos el menu inicial.')
        return redirect('menu_inicial')
        
    evaluaciones = EvaluacionDesempeno.objects.filter(colaborador=perfil).order_by('-periodo__fecha_inicio')
    
    return render(request, 'intranet/rrhh/desempeno/mis_evaluaciones.html', {
        'evaluaciones': evaluaciones
    })

@login_required
def evaluar_equipo(request):
    perfil = getattr(request.user, 'perfil', None)
    if not perfil:
        messages.info(request, 'No se encontro un perfil asociado. Te mostramos el menu inicial.')
        return redirect('menu_inicial')
        
    evaluaciones = EvaluacionDesempeno.objects.filter(evaluador=perfil).order_by('-periodo__fecha_inicio')
    
    return render(request, 'intranet/rrhh/desempeno/evaluar_equipo.html', {
        'evaluaciones': evaluaciones
    })

@login_required
def form_evaluacion(request, eval_id):
    evaluacion = get_object_or_404(EvaluacionDesempeno, id=eval_id)
    perfil = getattr(request.user, 'perfil', None)
    
    es_evaluador = (evaluacion.evaluador == perfil)
    es_evaluado = (evaluacion.colaborador == perfil)
    es_rrhh = perfil and perfil.rol in ['RRHH', 'ADMINISTRATIVO', 'GERENCIA']
    
    if not (es_evaluador or es_evaluado or es_rrhh):
        messages.error(request, "No tienes permiso para ver esta evaluación.")
        return redirect('menu_inicial')
        
    if request.method == 'POST':
        # Guardar autoevaluacion
        if es_evaluado and evaluacion.estado == 'PENDIENTE':
            evaluacion.autoevaluacion_comentario = request.POST.get('autoevaluacion_comentario', '')
            evaluacion.estado = 'AUTOEVALUADO'
            evaluacion.save()
            messages.success(request, "Autoevaluación guardada correctamente.")
            return redirect('mis_evaluaciones')
            
        # Guardar evaluacion por supervisor
        elif (es_evaluador or es_rrhh) and evaluacion.estado in ['PENDIENTE', 'AUTOEVALUADO']:
            total_kpis = evaluacion.detalles.count()
            if total_kpis > 0:
                suma_puntuacion = Decimal('0.0')
                for detalle in evaluacion.detalles.all():
                    resultado = request.POST.get(f'resultado_{detalle.id}')
                    comentario = request.POST.get(f'comentario_{detalle.id}')
                    if resultado:
                        detalle.resultado_real = Decimal(resultado)
                        detalle.calcular_puntuacion()
                        suma_puntuacion += detalle.puntuacion
                    if comentario:
                        detalle.comentario = comentario
                    detalle.save()
                
                evaluacion.nota_final = suma_puntuacion / total_kpis
                
            evaluacion.feedback_supervisor = request.POST.get('feedback_supervisor', '')
            evaluacion.potencial = request.POST.get('potencial')
            evaluacion.estado = 'EVALUADO'
            evaluacion.save()
            messages.success(request, "Evaluación completada correctamente.")
            return redirect('evaluar_equipo')

    return render(request, 'intranet/rrhh/desempeno/form_evaluacion.html', {
        'evaluacion': evaluacion,
        'es_evaluador': es_evaluador,
        'es_evaluado': es_evaluado,
        'es_rrhh': es_rrhh
    })
