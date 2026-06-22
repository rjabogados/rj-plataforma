import traceback
import openpyxl
import uuid
import json
import random 
from datetime import datetime, date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q, Prefetch
from django.utils import timezone
from django.http import HttpResponse

from intranet.models import (
    Colaborador, Negocio, Encuesta, Pregunta, RespuestaEncuesta,
    MensajeInterno, EventoCalendario, Comunicado, CandidatoOnboarding,
    MaterialFormativo, MatriculaCurso,
    PreguntaEvaluacion, RespuestaColaborador, OpcionRespuesta
)

from .utils import solo_directivos, solo_calidad, generar_username_unico
from intranet.models.lms import EvaluacionCurso, CursoInduccion

# ==========================================
# DIRECTORIO DE PERSONAL E IMPORTACIÓN EXCEL
# ==========================================
@login_required(login_url='login')
@solo_directivos
def colaboradores(request):
    if request.method == 'POST':
        nombres = request.POST.get('nombres')
        apellidos = request.POST.get('apellidos')
        dni_val = request.POST.get('dni').strip()
        correo_val = request.POST.get('correo').strip().lower() or None
        rol_val = request.POST.get('rol')
        negocio_id = request.POST.get('negocio')
        tipo_horario = request.POST.get('tipo_horario')
        
        username_custom = request.POST.get('username', '').strip()
        password_custom = request.POST.get('password', '').strip()

        username_final = username_custom if username_custom else generar_username_unico(nombres, apellidos, dni_val)
        password_final = password_custom if password_custom else dni_val

        negocio_instancia = Negocio.objects.get(id=negocio_id) if negocio_id else None
        f_ingreso = request.POST.get('fecha_ingreso')
        fecha_formal = datetime.strptime(f_ingreso, '%Y-%m-%d').date() if f_ingreso else date.today()

        if not User.objects.filter(username=username_final).exists():
            nuevo_user = User.objects.create_user(
                username=username_final, email=correo_val if correo_val else "",
                password=password_final, first_name=nombres, last_name=apellidos
            )
            Colaborador.objects.create(
                user=nuevo_user, dni=dni_val, rol=rol_val, negocio=negocio_instancia, 
                tipo_horario=tipo_horario, hora_ingreso=request.POST.get('hora_ingreso') or None, 
                hora_salida=request.POST.get('hora_salida') or None, fecha_ingreso=fecha_formal
            )
            return redirect('colaboradores')

    query = request.GET.get('q', '').strip()
    if query:
        lista_colaboradores = Colaborador.objects.filter(
            Q(user__first_name__icontains=query) | Q(user__last_name__icontains=query) | Q(dni__icontains=query)
        ).select_related('user', 'negocio')
    else:
        lista_colaboradores = Colaborador.objects.all().select_related('user', 'negocio')

    return render(request, 'intranet/colaboradores.html', {
        'colaboradores': lista_colaboradores, 'negocios': Negocio.objects.all(), 
        'roles': Colaborador.ROLES, 'tipos_horario': Colaborador.TIPO_HORARIO, 'query': query
    })

@login_required(login_url='login')
@solo_directivos
def editar_colaborador(request, pk):
    colab = get_object_or_404(Colaborador, pk=pk)
    
    if request.method == 'POST':
        colab.user.first_name = request.POST.get('nombres')
        colab.user.last_name = request.POST.get('apellidos')
        colab.user.email = request.POST.get('correo').strip().lower() or ""
        
        nuevo_username = request.POST.get('username', '').strip()
        nueva_password = request.POST.get('password', '').strip()

        if nuevo_username and not User.objects.filter(username=nuevo_username).exclude(pk=colab.user.pk).exists():
            colab.user.username = nuevo_username
            
        if nueva_password:
            colab.user.set_password(nueva_password)

        colab.user.save()
        colab.dni = request.POST.get('dni').strip()
        colab.rol = request.POST.get('rol')
        colab.tipo_horario = request.POST.get('tipo_horario')
        colab.hora_ingreso = request.POST.get('hora_ingreso') or None
        colab.hora_salida = request.POST.get('hora_salida') or None
        if request.POST.get('fecha_ingreso'):
            colab.fecha_ingreso = datetime.strptime(request.POST.get('fecha_ingreso'), '%Y-%m-%d').date()
        
        negocio_id = request.POST.get('negocio')
        colab.negocio = Negocio.objects.get(id=negocio_id) if negocio_id else None
        colab.save()

        onboarding_activo = request.POST.get('switch_onboarding') == 'on'
        
        if onboarding_activo:
            CandidatoOnboarding.objects.get_or_create(
                colaborador=colab, dni=colab.dni,
                defaults={
                    'nombres': colab.user.first_name,
                    'apellidos': colab.user.last_name,
                    'estado': 'EN_PROCESO'
                }
            )
        else:
            CandidatoOnboarding.objects.filter(colaborador=colab).delete()

        return redirect('colaboradores')
        
    tiene_onboarding = CandidatoOnboarding.objects.filter(colaborador=colab).exists()
    return render(request, 'intranet/editar_colaborador.html', {
        'colab': colab, 'negocios': Negocio.objects.all(), 'tiene_onboarding': tiene_onboarding
    })

@login_required(login_url='login')
@solo_directivos
def eliminar_colaborador(request, pk):
    colab = get_object_or_404(Colaborador, pk=pk)
    user_vinculado = colab.user
    colab.delete()
    if user_vinculado: user_vinculado.delete()
    return redirect('colaboradores')

@login_required(login_url='login')
@solo_directivos
def mapear_excel(request):
    if request.method == 'POST' and request.FILES.get('archivo_excel'):
        excel_file = request.FILES['archivo_excel']
        nombre_tmp = default_storage.save(f'tmp/{request.user.id}_import.xlsx', ContentFile(excel_file.read()))
        wb = openpyxl.load_workbook(default_storage.open(nombre_tmp))
        cabeceras_excel = [str(celda.value).strip() for celda in wb.active[1] if celda.value is not None]
        request.session['ruta_excel_tmp'] = nombre_tmp
        return render(request, 'intranet/mapear_excel.html', {'cabeceras': cabeceras_excel})
    return redirect('colaboradores')

@login_required(login_url='login')
def procesar_mapeo_balotario(request):
    if request.method == 'POST':
        try:
            ruta_archivo = request.session.get('ruta_excel_balotario')
            if not ruta_archivo or not default_storage.exists(ruta_archivo):
                messages.error(request, "El archivo expiró. Vuelve a subirlo.")
                return redirect('gestor_lms')

            idx_pregunta = int(request.POST.get('prop_pregunta', -1))
            idx_correcta = int(request.POST.get('prop_correcta', -1))
            idx_alt1 = int(request.POST.get('prop_alt1', -1))
            idx_alt2 = int(request.POST.get('prop_alt2', -1))
            idx_alt3 = int(request.POST.get('prop_alt3', -1))
            idx_alt4 = int(request.POST.get('prop_alt4', -1))

            archivo_excel = default_storage.open(ruta_archivo)
            wb = openpyxl.load_workbook(archivo_excel, data_only=True, read_only=True)
            
            preguntas_temporales = []
            for i, fila in enumerate(wb.active.iter_rows(min_row=2, values_only=True)):
                def get_val(idx):
                    if idx != -1 and idx < len(fila):
                        val = fila[idx]
                        return str(val).strip() if val is not None else ""
                    return ""

                enunciado = get_val(idx_pregunta)
                if enunciado: 
                    preguntas_temporales.append({
                        'id_temp': int(i),
                        'enunciado': enunciado,
                        'correcta': get_val(idx_correcta),
                        'alt1': get_val(idx_alt1), 
                        'alt2': get_val(idx_alt2), 
                        'alt3': get_val(idx_alt3), 
                        'alt4': get_val(idx_alt4)
                    })

            wb.close()
            archivo_excel.close()
            try:
                default_storage.delete(ruta_archivo)
            except Exception: pass 
            
            if 'ruta_excel_balotario' in request.session:
                del request.session['ruta_excel_balotario']

            request.session['balotario_temporal'] = preguntas_temporales
            request.session.save()
            return redirect('previsualizar_balotario')
        except Exception as e:
            error_texto = traceback.format_exc()
            return HttpResponse(f"<div style='padding:20px; font-family: monospace; background:#ffe6e6; color:red; border:2px solid red;'><h2>¡EL ERROR FUE ATRAPADO!</h2><pre>{error_texto}</pre></div>", status=200)
    return redirect('gestor_lms')


# ==========================================
# ONBOARDING CORPORATIVO (INDUCCIÓN)
# ==========================================
@login_required(login_url='login')
def induccion(request): return redirect('mi_induccion')

@login_required(login_url='login')
@solo_calidad
def induccion_admin(request): return redirect('onboarding_admin')

@login_required(login_url='login')
@solo_directivos
def gestionar_onboarding(request): return redirect('onboarding_admin')

@login_required(login_url='login')
@solo_directivos
def onboarding_admin(request):
    if request.method == 'POST':
        if 'crear_modulo' in request.POST:
            titulo = request.POST.get('titulo')
            descripcion = request.POST.get('descripcion')
            CursoInduccion.objects.create(titulo=titulo, descripcion=descripcion, tipo='INDUCCION')
            messages.success(request, f"Módulo de Inducción '{titulo}' creado exitosamente.")
        else:
            nombres_val = request.POST.get('nombres')
            apellidos_val = request.POST.get('apellidos')
            dni_val = request.POST.get('dni')
            telefono_val = request.POST.get('telefono', '')
            puesto_val = request.POST.get('puesto_esperado', 'ASESOR')
            negocio_id = request.POST.get('campaña_destino')
            
            if CandidatoOnboarding.objects.filter(dni=dni_val).exists():
                messages.error(request, f"El DNI {dni_val} ya se encuentra registrado.")
            else:
                CandidatoOnboarding.objects.create(nombres=nombres_val, apellidos=apellidos_val, dni=dni_val, telefono=telefono_val, puesto_esperado=puesto_val, campaña_destino_id=negocio_id if negocio_id else None)
                messages.success(request, "Postulante registrado correctamente.")
        return redirect('onboarding_admin')

    onboardings_activos = CandidatoOnboarding.objects.all().select_related('colaborador__user', 'campaña_destino')
    lista_candidatos_progreso = []
    for item in onboardings_activos:
        if item.colaborador:
            matriculas = MatriculaCurso.objects.filter(colaborador=item.colaborador)
            total_cursos = matriculas.count()
            completados = matriculas.filter(estado='COMPLETADO').count()
            porcentaje = int((completados / total_cursos) * 100) if total_cursos > 0 else 0
            ratio = f"{completados}/{total_cursos}"
        else:
            porcentaje = item.porcentaje_expediente()
            ratio = "Expediente"
        lista_candidatos_progreso.append({'onboarding': item, 'porcentaje': porcentaje, 'ratio': ratio})

    cursos_biblioteca = CursoInduccion.objects.filter(activo=True, tipo='INDUCCION').order_by('-fecha_creacion')
    negocios = Negocio.objects.all()

    return render(request, 'intranet/onboarding_lista.html', {
        'candidatos_progreso': lista_candidatos_progreso, 'candidatos': onboardings_activos, 
        'modulos_biblioteca': cursos_biblioteca, 'negocios': negocios
    })

@login_required(login_url='login')
@solo_directivos
def asignar_modulos_induccion(request, colab_id):
    colaborador = get_object_or_404(Colaborador, id=colab_id)
    cursos_disponibles = CursoInduccion.objects.filter(activo=True, tipo='INDUCCION').order_by('-fecha_creacion')
    
    if request.method == 'POST':
        cursos_seleccionados = request.POST.getlist('modulos_ids')
        MatriculaCurso.objects.filter(colaborador=colaborador).exclude(curso_id__in=cursos_seleccionados).exclude(estado='COMPLETADO').delete()
        for c_id in cursos_seleccionados: MatriculaCurso.objects.get_or_create(colaborador=colaborador, curso_id=c_id)
        messages.success(request, f"Malla formativa de Inducción actualizada para {colaborador.user.first_name}.")
        return redirect('onboarding_admin')
        
    cursos_actuales = MatriculaCurso.objects.filter(colaborador=colaborador).values_list('curso_id', flat=True)
    return render(request, 'intranet/asignar_modulos.html', {'colaborador': colaborador, 'modulos_disponibles': cursos_disponibles, 'modulos_actuales': cursos_actuales})

@login_required(login_url='login')
def mi_induccion(request):
    try:
        colaborador = request.user.perfil
    except:
        messages.error(request, "Tu usuario no tiene un perfil de trabajador asociado.")
        return redirect('inicio')

    cursos_disponibles = CursoInduccion.objects.filter(
        Q(publico_general=True) | 
        Q(rol_permitido=colaborador.rol) | 
        Q(cartera_vinculada=colaborador.negocio),
        activo=True,
        tipo='INDUCCION' 
    ).distinct()

    mis_modulos = []
    for curso in cursos_disponibles:
        matricula, created = MatriculaCurso.objects.get_or_create(
            colaborador=colaborador, 
            curso=curso,
            defaults={'estado': 'PENDIENTE'}
        )
        mis_modulos.append(matricula)

    if request.method == 'POST' and 'marcar_completado' in request.POST:
        progreso_id = request.POST.get('progreso_id')
        matricula_actualizar = MatriculaCurso.objects.get(id=progreso_id, colaborador=colaborador)
        matricula_actualizar.estado = 'COMPLETADO'
        matricula_actualizar.fecha_finalizacion = timezone.now()
        matricula_actualizar.save()
        messages.success(request, f"¡Módulo '{matricula_actualizar.curso.titulo}' completado con éxito!")
        return redirect('mi_induccion')

    total_modulos = len(mis_modulos)
    completados = sum(1 for m in mis_modulos if m.estado == 'COMPLETADO')
    porcentaje = int((completados / total_modulos) * 100) if total_modulos > 0 else 0

    return render(request, 'intranet/mi_induccion.html', {
        'mis_modulos': mis_modulos,
        'total': total_modulos,
        'completados': completados,
        'porcentaje': porcentaje
    })

@login_required(login_url='login')
@solo_directivos
def actualizar_expediente(request, candidato_id):
    candidato = get_object_or_404(CandidatoOnboarding, id=candidato_id)
    if request.method == 'POST':
        candidato.doc_cv = request.POST.get('doc_cv') == 'on'
        candidato.doc_dni = request.POST.get('doc_dni') == 'on'
        candidato.doc_antecedentes = request.POST.get('doc_antecedentes') == 'on'
        candidato.doc_recibo_servicios = request.POST.get('doc_recibo_servicios') == 'on'
        candidato.save()
        messages.success(request, f"Expediente de {candidato.nombres} actualizado.")
    return redirect('onboarding_admin')

@login_required(login_url='login')
@solo_directivos
def pasar_a_planilla(request, candidato_id):
    candidato = get_object_or_404(CandidatoOnboarding, id=candidato_id)
    if candidato.porcentaje_expediente() < 100:
        messages.error(request, "Expediente incompleto. Faltan documentos.")
        return redirect('onboarding_admin')
    try:
        with transaction.atomic():
            if candidato.colaborador:
                candidato.estado = 'COMPLETADO'
                candidato.save()
            else:
                username_final = f"{candidato.nombres.split()[0].lower()}.{candidato.apellidos.split()[0].lower()}"
                if User.objects.filter(username=username_final).exists():
                    username_final = f"{username_final}{candidato.dni[-2:]}"
                nuevo_user = User.objects.create_user(username=username_final, email=candidato.correo or '', password=candidato.dni, first_name=candidato.nombres, last_name=candidato.apellidos)
                nuevo_colaborador = Colaborador.objects.create(user=nuevo_user, dni=candidato.dni, rol=candidato.puesto_esperado, negocio=candidato.campaña_destino, fecha_ingreso=date.today())
                candidato.colaborador = nuevo_colaborador
                candidato.estado = 'COMPLETADO'
                candidato.save()
                messages.success(request, f"¡{candidato.nombres} ingresó a planilla!")
    except Exception:
        messages.error(request, "Error al procesar el alta. Verifique el DNI.")
    return redirect('onboarding_admin')

# ==========================================
# MOTOR DE ENCUESTAS, COMUNICADOS, CALENDARIO...
# ==========================================
@login_required(login_url='login')
def encuestas_personal(request): return render(request, 'intranet/encuestas_personal.html', {'encuestas': Encuesta.objects.filter(activa=True).order_by('-fecha_creacion')})
@login_required(login_url='login')
@solo_directivos
def encuestas_admin(request): return render(request, 'intranet/encuestas_admin.html', {'encuestas': Encuesta.objects.all().prefetch_related('preguntas')})
@login_required(login_url='login')
@solo_directivos
def resultados_encuesta(request, pk): return render(request, 'intranet/encuesta_resultados.html')
@login_required(login_url='login')
@solo_directivos
def exportar_encuesta(request, pk): return HttpResponse("Exportar")
@login_required(login_url='login')
def mensajeria(request): return render(request, 'intranet/mensajeria.html')
@login_required(login_url='login')
def leer_mensaje(request, pk): return render(request, 'intranet/leer_mensaje.html')
@login_required(login_url='login')
def calendario(request): return render(request, 'intranet/calendario.html')
@login_required(login_url='login')
def comunicados(request): return render(request, 'intranet/comunicados.html')
@login_required(login_url='login')
@solo_directivos
def gestor_comunicados(request): return render(request, 'intranet/gestor_comunicados.html')
@login_required(login_url='login')
@solo_directivos
def eliminar_comunicado(request, pk): return redirect('gestor_comunicados')
@login_required(login_url='login')
@solo_directivos
def eliminar_evento(request, pk): return redirect('calendario')
@login_required(login_url='login')
@solo_directivos
def eliminar_candidato(request, pk): return redirect('dashboard')
@login_required(login_url='login')
@solo_directivos
def activos(request): return render(request, 'intranet/activos.html')
@login_required(login_url='login')
def beneficios(request): return render(request, 'intranet/beneficios.html')


# ==========================================
# ACADEMIA LMS: GESTOR Y EXÁMENES
# ==========================================
@login_required(login_url='login')
@solo_directivos
def gestor_lms(request):
    from intranet.models.rrhh_core import Negocio, Colaborador

    if request.method == 'POST':
        if 'crear_curso' in request.POST:
            titulo = request.POST.get('titulo')
            descripcion = request.POST.get('descripcion')
            publico_general = request.POST.get('publico_general') == 'on'
            rol_permitido = request.POST.get('rol_permitido') or None
            cartera_id = request.POST.get('cartera_vinculada')
            cartera_obj = Negocio.objects.filter(id=cartera_id).first() if cartera_id else None

            CursoInduccion.objects.create(
                titulo=titulo,
                descripcion=descripcion,
                tipo='ACADEMIA', 
                publico_general=publico_general,
                rol_permitido=rol_permitido,
                cartera_vinculada=cartera_obj
            )
            messages.success(request, f"¡Curso '{titulo}' creado exitosamente en la Academia LMS!")
            return redirect('gestor_lms')

        elif 'crear_evaluacion' in request.POST:
            curso_id = request.POST.get('curso_id')
            titulo = request.POST.get('titulo')
            instrucciones = request.POST.get('instrucciones', '')
            p_maximo = request.POST.get('puntaje_maximo', 20.00)
            p_aprobatorio = request.POST.get('puntaje_aprobatorio', 14.00)
            p_mostrar = request.POST.get('preguntas_a_mostrar', 10)
            aleatorio = request.POST.get('orden_aleatorio') == 'on'

            curso = get_object_or_404(CursoInduccion, id=curso_id)

            if hasattr(curso, 'evaluacion'):
                messages.error(request, f"El curso '{curso.titulo}' ya tiene una evaluación configurada.")
            else:
                EvaluacionCurso.objects.create(
                    curso=curso, titulo=titulo, instrucciones=instrucciones,
                    puntaje_maximo=p_maximo, puntaje_aprobatorio=p_aprobatorio,
                    preguntas_a_mostrar=p_mostrar, orden_aleatorio=aleatorio
                )
                messages.success(request, "¡Examen creado! Ahora puedes subir el balotario de preguntas.")
            return redirect('gestor_lms')

    cursos_disponibles = CursoInduccion.objects.filter(activo=True, tipo='ACADEMIA')
    evaluaciones = EvaluacionCurso.objects.filter(curso__tipo='ACADEMIA').select_related('curso').prefetch_related('preguntas_balotario')
    
    return render(request, 'intranet/lms/gestor_lms.html', {
        'cursos': cursos_disponibles,
        'evaluaciones': evaluaciones,
        'negocios': Negocio.objects.all(),
        'roles': Colaborador.ROLES
    })

@login_required(login_url='login')
def academia(request):
    try:
        colaborador = request.user.perfil
    except:
        messages.error(request, "Tu usuario no tiene un perfil de trabajador asociado.")
        return redirect('inicio')

    cursos_disponibles = CursoInduccion.objects.filter(
        Q(publico_general=True) | 
        Q(rol_permitido=colaborador.rol) | 
        Q(cartera_vinculada=colaborador.negocio),
        activo=True,
        tipo='ACADEMIA'
    ).distinct()

    mis_cursos = []
    for curso in cursos_disponibles:
        matricula, created = MatriculaCurso.objects.get_or_create(
            colaborador=colaborador, 
            curso=curso,
            defaults={'estado': 'PENDIENTE'}
        )
        mis_cursos.append(matricula)

    total_cursos = len(mis_cursos)
    completados = sum(1 for m in mis_cursos if m.estado == 'COMPLETADO')
    porcentaje = int((completados / total_cursos) * 100) if total_cursos > 0 else 0

    return render(request, 'intranet/academia.html', {
        'mis_cursos': mis_cursos,
        'total': total_cursos,
        'completados': completados,
        'porcentaje': porcentaje
    })

@login_required(login_url='login')
@solo_directivos
def importar_excel_balotario(request, evaluacion_id):
    evaluacion = get_object_or_404(EvaluacionCurso, id=evaluacion_id)
    if request.method == 'POST' and request.FILES.get('archivo_excel'):
        excel_file = request.FILES['archivo_excel']
        try:
            nombre_tmp = default_storage.save(f'tmp/balotario_{request.user.id}.xlsx', ContentFile(excel_file.read()))
            wb = openpyxl.load_workbook(default_storage.open(nombre_tmp))
            cabeceras_excel = [str(celda.value).strip() for celda in wb.active[1] if celda.value is not None]
            request.session['ruta_excel_balotario'] = nombre_tmp
            request.session['evaluacion_id_temporal'] = evaluacion.id
            request.session.modified = True
            return render(request, 'intranet/lms/mapear_balotario.html', {'cabeceras': cabeceras_excel, 'evaluacion': evaluacion})
        except Exception as e:
            messages.error(request, f"Ocurrió un error leyendo el Excel: {str(e)}")
            return redirect('gestor_lms')
    return render(request, 'intranet/lms/subir_excel.html', {'evaluacion': evaluacion})

@login_required(login_url='login')
@solo_directivos
def previsualizar_y_guardar_balotario(request):
    try:
        preguntas = request.session.get('balotario_temporal')
        eval_id = request.session.get('evaluacion_id_temporal')

        if not preguntas or not eval_id:
            messages.warning(request, "No hay ningún balotario pendiente en memoria.")
            return redirect('gestor_lms')

        evaluacion = get_object_or_404(EvaluacionCurso, id=eval_id)

        if request.method == 'POST':
            with transaction.atomic():
                
                # --- LIMPIEZA ANTI-DUPLICADOS (Borrador automático) ---
                evaluacion.preguntas_balotario.all().delete()
                # ------------------------------------------------------

                ids_llegados = [k.split('_')[1] for k in request.POST if k.startswith('enunciado_')]
                if ids_llegados:
                    puntos_por_pregunta = round(evaluacion.puntaje_maximo / len(ids_llegados), 2)
                else:
                    puntos_por_pregunta = 0.00

                # 2. Guardamos formalmente
                for idx in ids_llegados:
                    enunciado_texto = request.POST.get(f'enunciado_{idx}')
                    
                    # Evitamos guardar preguntas que lleguen vacías
                    if not enunciado_texto or not enunciado_texto.strip():
                        continue

                    nueva_pregunta = PreguntaEvaluacion.objects.create(
                        evaluacion=evaluacion,
                        enunciado=enunciado_texto.strip(),
                        puntos=puntos_por_pregunta
                    )

                    opcion_correcta_id = request.POST.get(f'correcta_{idx}')
                    textos_agregados = set()  # <--- FILTRO MÁGICO: Evita duplicar textos en la misma pregunta
                    
                    for i in range(1, 5):
                        txt_alt = request.POST.get(f'alt{i}_{idx}')
                        
                        # Si la caja estaba vacía (ej: V o F de solo 2 opciones), la ignoramos por completo
                        if txt_alt and txt_alt.strip():
                            texto_limpio = txt_alt.strip()
                            texto_lower = texto_limpio.lower()
                            
                            # Si no hemos guardado esta opción antes, la agregamos
                            if texto_lower not in textos_agregados:
                                es_correcta = (str(i) == str(opcion_correcta_id))
                                OpcionRespuesta.objects.create(pregunta=nueva_pregunta, texto=texto_limpio, es_correcta=es_correcta)
                                textos_agregados.add(texto_lower)

            del request.session['balotario_temporal']
            del request.session['evaluacion_id_temporal']

            messages.success(request, "¡Balotario mapeado e inyectado con éxito!")
            return redirect('gestor_lms')

        return render(request, 'intranet/lms/previsualizar_balotario.html', {'preguntas': preguntas, 'evaluacion': evaluacion})

    except Exception as e:
        import traceback
        return HttpResponse(f"<h2>¡Atrapado en la inyección! El error real es:</h2><pre style='background:#eee; padding:20px;'>{traceback.format_exc()}</pre>")

@login_required(login_url='login')
def rendir_evaluacion(request, matricula_id):
    perfil = request.user.perfil
    matricula = get_object_or_404(MatriculaCurso, id=matricula_id, colaborador=perfil)
    
    if not hasattr(matricula.curso, 'evaluacion'):
        messages.error(request, "Este curso aún no tiene un examen configurado.")
        return redirect('academia')
        
    evaluacion = matricula.curso.evaluacion

    if matricula.estado in ['COMPLETADO', 'REPROBADO']:
        messages.info(request, f"Ya rendiste este examen. Tu nota final fue: {matricula.nota_obtenida}")
        return redirect('academia')

    if request.method == 'POST':
        nota_final = 0.00
        preguntas_ids = request.POST.getlist('preguntas_mostradas')
        preguntas_evaluadas = PreguntaEvaluacion.objects.filter(id__in=preguntas_ids).prefetch_related('alternativas')

        with transaction.atomic():
            for pregunta in preguntas_evaluadas:
                opcion_marcada_id = request.POST.get(f'pregunta_{pregunta.id}')
                puntos_ganados = 0.00
                es_correcta = False
                opcion_obj = None

                if opcion_marcada_id:
                    opcion_obj = pregunta.alternativas.filter(id=opcion_marcada_id).first()
                    if opcion_obj and opcion_obj.es_correcta:
                        puntos_ganados = float(pregunta.puntos)
                        es_correcta = True
                        nota_final += puntos_ganados

                respuesta_registro = RespuestaColaborador.objects.create(
                    matricula=matricula, pregunta=pregunta, es_correcta=es_correcta, puntos_obtenidos=puntos_ganados
                )
                if opcion_obj:
                    respuesta_registro.opciones_marcadas.add(opcion_obj)

            matricula.nota_obtenida = nota_final
            matricula.fecha_finalizacion = timezone.now()
            
            if nota_final >= float(evaluacion.puntaje_aprobatorio):
                matricula.estado = 'COMPLETADO'
                messages.success(request, f"¡Felicidades! Has aprobado el examen con {nota_final} puntos.")
            else:
                matricula.estado = 'REPROBADO'
                messages.error(request, f"No alcanzaste la nota mínima. Obtuviste {nota_final} puntos. Deberás repasar los materiales.")
            
            matricula.save()
            return redirect('academia')

    if matricula.estado != 'EVALUANDO':
        matricula.estado = 'EVALUANDO'
        matricula.save()

    if evaluacion.orden_aleatorio:
        preguntas_qs = evaluacion.preguntas_balotario.filter(activa=True).order_by('?')[:evaluacion.preguntas_a_mostrar]
    else:
        preguntas_qs = evaluacion.preguntas_balotario.filter(activa=True).order_by('id')[:evaluacion.preguntas_a_mostrar]

    # --- EL CHOCOLATEO DE OPCIONES ---
    preguntas = list(preguntas_qs)
    
    for p in preguntas:
        opciones = list(p.alternativas.all())
        random.shuffle(opciones)
        # Guardamos la lista barajada para usarla en el HTML
        p.opciones_mezcladas = opciones

    return render(request, 'intranet/lms/rendir_examen.html', {'matricula': matricula, 'evaluacion': evaluacion, 'preguntas': preguntas})

@login_required(login_url='login')
@solo_directivos
def resultados_evaluacion(request, evaluacion_id):
    evaluacion = get_object_or_404(EvaluacionCurso, id=evaluacion_id)
    matriculas = MatriculaCurso.objects.filter(curso=evaluacion.curso).select_related('colaborador__user')
    
    completados = matriculas.filter(estado__in=['COMPLETADO', 'REPROBADO'])
    total_completados = completados.count()
    
    promedio = 0
    if total_completados > 0:
        promedio = sum(m.nota_obtenida for m in completados) / total_completados
        
    aprobados = matriculas.filter(estado='COMPLETADO').count()
    reprobados = matriculas.filter(estado='REPROBADO').count()

   # Preparamos los datos matemáticos para los gráficos circulares
    graficos = []
    for pregunta in evaluacion.preguntas_balotario.filter(activa=True):
        opciones = pregunta.alternativas.all()
        labels = [op.texto for op in opciones]
        data = []
        for op in opciones:
            cantidad_votos = RespuestaColaborador.objects.filter(pregunta=pregunta, opciones_marcadas=op).count()
            data.append(cantidad_votos)
        
        graficos.append({
            'id': pregunta.id,
            'enunciado': pregunta.enunciado,
            'labels': labels, # <-- Lo dejamos como una lista normal de Python
            'data': data      # <-- Lo dejamos como una lista normal de Python
        })

    return render(request, 'intranet/lms/resultados_evaluacion.html', {
        'evaluacion': evaluacion,
        'matriculas': matriculas,
        'promedio': round(promedio, 2),
        'aprobados': aprobados,
        'reprobados': reprobados,
        'total_completados': total_completados,
        'graficos': graficos
    })

@login_required(login_url='login')
@solo_directivos
def reabrir_examen(request, matricula_id):
    matricula = get_object_or_404(MatriculaCurso, id=matricula_id)
    evaluacion_id = matricula.curso.evaluacion.id
    
    # Reseteamos los valores para que pueda darlo de nuevo
    matricula.estado = 'PENDIENTE'
    matricula.nota_obtenida = 0.00
    matricula.fecha_finalizacion = None
    matricula.save()
    
    # Destruimos sus respuestas anteriores para dejar la hoja en blanco
    RespuestaColaborador.objects.filter(matricula=matricula).delete()
    
    messages.success(request, f"Examen reabierto exitosamente para {matricula.colaborador.user.first_name}.")
    return redirect('resultados_evaluacion', evaluacion_id=evaluacion_id)

@login_required(login_url='login')
@solo_directivos
def exportar_resultados_lms(request, evaluacion_id):
    evaluacion = get_object_or_404(EvaluacionCurso, id=evaluacion_id)
    matriculas = MatriculaCurso.objects.filter(curso=evaluacion.curso, estado__in=['COMPLETADO', 'REPROBADO'])
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Resultados Examen"
    
    # Cabeceras Base
    headers = ['Colaborador', 'DNI', 'Nota Obtenida', 'Estado', 'Fecha Examen']
    preguntas = evaluacion.preguntas_balotario.filter(activa=True).order_by('id')
    
    # Agregamos las preguntas como cabeceras en el Excel
    for p in preguntas:
        headers.append(p.enunciado)
        
    ws.append(headers)
    
    # Llenamos la data de los colaboradores
    for m in matriculas:
        row = [
            f"{m.colaborador.user.first_name} {m.colaborador.user.last_name}",
            m.colaborador.dni,
            float(m.nota_obtenida),
            m.estado,
            m.fecha_finalizacion.strftime('%Y-%m-%d %H:%M') if m.fecha_finalizacion else ''
        ]
        
        # Buscamos qué marcó exactamente en cada pregunta
        for p in preguntas:
            resp = RespuestaColaborador.objects.filter(matricula=m, pregunta=p).first()
            if resp and resp.opciones_marcadas.exists():
                marcada = resp.opciones_marcadas.first().texto
                row.append(marcada)
            else:
                row.append("-")
        ws.append(row)
        
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="Resultados_{evaluacion.titulo}.xlsx"'
    wb.save(response)
    return response