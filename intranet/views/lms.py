# Force update for Render deploy

import traceback
import openpyxl
import uuid
import json
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

# Importamos los modelos (Agregué OpcionRespuesta al final)
from intranet.models import (
    Colaborador, Negocio, Encuesta, Pregunta, RespuestaEncuesta,
    MensajeInterno, EventoCalendario, Comunicado, CandidatoOnboarding,
    MaterialFormativo, MatriculaCurso,
    PreguntaEvaluacion, RespuestaColaborador, OpcionRespuesta
)

# Herramientas globales de tu archivo utils.py
from .utils import solo_directivos, solo_calidad, generar_username_unico

from intranet.models.lms import EvaluacionCurso, CursoInduccion # Asegúrate de que las importaciones sean correctas

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

import sys
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

@login_required(login_url='login')
def procesar_mapeo_balotario(request):
    if request.method == 'POST':
        try:
            ruta_archivo = request.session.get('ruta_excel_balotario')
            eval_id = request.session.get('evaluacion_id_temporal')
            
            if not ruta_archivo or not default_storage.exists(ruta_archivo):
                messages.error(request, "El archivo expiró. Vuelve a subirlo.")
                return redirect('gestor_lms')

            evaluacion = get_object_or_404(EvaluacionCurso, id=eval_id)
            
            # 1. LA CURA AL VENENO DE SESIÓN: Forzar explícitamente a float
            puntos_calc = evaluacion.puntaje_maximo / evaluacion.preguntas_a_mostrar if evaluacion.preguntas_a_mostrar > 0 else 0
            puntos_automaticos = float(round(puntos_calc, 2))

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
                    if 0 <= idx < len(fila):
                        val = fila[idx]
                        return str(val).strip() if val is not None else ""
                    return ""

                enunciado = get_val(idx_pregunta)
                correcta = get_val(idx_correcta)
                alt1 = get_val(idx_alt1)
                alt2 = get_val(idx_alt2)
                alt3 = get_val(idx_alt3)
                alt4 = get_val(idx_alt4)

                if enunciado and correcta and alt1: 
                    preguntas_temporales.append({
                        'id_temp': int(i),
                        'enunciado': enunciado,
                        'correcta': correcta,
                        'alt1': alt1, 'alt2': alt2, 'alt3': alt3, 'alt4': alt4,
                        'puntos': puntos_automaticos # Ahora es un float seguro
                    })

            wb.close()
            archivo_excel.close()
            
            # Limpieza segura
            try:
                default_storage.delete(ruta_archivo)
            except Exception:
                pass # Si el archivo ya se borró, ignoramos el error
            
            if 'ruta_excel_balotario' in request.session:
                del request.session['ruta_excel_balotario']

            request.session['balotario_temporal'] = preguntas_temporales
            
            # 2. LA TRAMPA MAESTRA: Forzamos el guardado AQUÍ MISMO
            request.session.save()
            
            return redirect('previsualizar_balotario')
            
        except Exception as e:
            # Ahora SÍ atraparemos cualquier error de sesión o de lectura
            error_texto = traceback.format_exc()
            return HttpResponse(
                f"<div style='padding:20px; font-family: monospace; background:#ffe6e6; color:red; border:2px solid red;'>"
                f"<h2>¡EL ERROR FUE ATRAPADO!</h2><pre>{error_texto}</pre></div>", 
                status=200
            )
            
    return redirect('gestor_lms')

# ==========================================
# ONBOARDING CORPORATIVO
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
            tipo = request.POST.get('tipo', 'GENERAL')
            CursoInduccion.objects.create(titulo=titulo, descripcion=descripcion, tipo=tipo)
            messages.success(request, f"Curso '{titulo}' creado en la academia LMS.")
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

    cursos_biblioteca = CursoInduccion.objects.filter(activo=True).order_by('-fecha_creacion')
    negocios = Negocio.objects.all()

    return render(request, 'intranet/onboarding_lista.html', {
        'candidatos_progreso': lista_candidatos_progreso, 'candidatos': onboardings_activos, 
        'modulos_biblioteca': cursos_biblioteca, 'negocios': negocios
    })

@login_required(login_url='login')
@solo_directivos
def asignar_modulos_induccion(request, colab_id):
    colaborador = get_object_or_404(Colaborador, id=colab_id)
    cursos_disponibles = CursoInduccion.objects.filter(activo=True).order_by('-fecha_creacion')
    
    if request.method == 'POST':
        cursos_seleccionados = request.POST.getlist('modulos_ids')
        MatriculaCurso.objects.filter(colaborador=colaborador).exclude(curso_id__in=cursos_seleccionados).exclude(estado='COMPLETADO').delete()
        for c_id in cursos_seleccionados: MatriculaCurso.objects.get_or_create(colaborador=colaborador, curso_id=c_id)
        messages.success(request, f"Malla formativa actualizada para {colaborador.user.first_name}.")
        return redirect('onboarding_admin')
        
    cursos_actuales = MatriculaCurso.objects.filter(colaborador=colaborador).values_list('curso_id', flat=True)
    return render(request, 'intranet/asignar_modulos.html', {'colaborador': colaborador, 'modulos_disponibles': cursos_disponibles, 'modulos_actuales': cursos_actuales})

@login_required(login_url='login')
def mi_induccion(request):
    try:
        colaborador = request.user.perfil
    except:
        messages.error(request, "Tu usuario no tiene un perfil de trabajador asociado.")
        return redirect('home')

    # 1. EL MOTOR DE SMART TARGETING: Buscamos cursos que hagan "Match" con el empleado
    cursos_disponibles = CursoInduccion.objects.filter(
        Q(publico_general=True) | 
        Q(rol_permitido=colaborador.rol) | 
        Q(cartera_vinculada=colaborador.negocio),
        activo=True
    ).distinct()

    # 2. AUTO-MATRÍCULA INVISIBLE: Creamos el registro si no existe
    mis_modulos = []
    for curso in cursos_disponibles:
        matricula, created = MatriculaCurso.objects.get_or_create(
            colaborador=colaborador, 
            curso=curso,
            defaults={'estado': 'PENDIENTE'}
        )
        mis_modulos.append(matricula)

    # 3. LÓGICA DE BOTONES (Si hizo clic en "Marcar como Completado" manual)
    if request.method == 'POST' and 'marcar_completado' in request.POST:
        progreso_id = request.POST.get('progreso_id')
        matricula_actualizar = MatriculaCurso.objects.get(id=progreso_id, colaborador=colaborador)
        matricula_actualizar.estado = 'COMPLETADO'
        from django.utils import timezone
        matricula_actualizar.fecha_finalizacion = timezone.now()
        matricula_actualizar.save()
        messages.success(request, f"¡Módulo '{matricula_actualizar.curso.titulo}' completado con éxito!")
        return redirect('mi_induccion')

    # 4. CÁLCULO DE PROGRESO DE LA BARRA
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
# MOTOR DE ENCUESTAS
# ==========================================
@login_required(login_url='login')
def encuestas_personal(request):
    perfil = getattr(request.user, 'perfil', None)
    if request.method == 'POST' and 'enviar_encuesta' in request.POST:
        enc_id = request.POST.get('encuesta_id')
        encuesta_obj = get_object_or_404(Encuesta, id=enc_id)
        sesion_uuid = str(uuid.uuid4())
        for pregunta in encuesta_obj.preguntas.all():
            valor = request.POST.get(f"pregunta_{pregunta.id}")
            if valor:
                resp = RespuestaEncuesta(pregunta=pregunta, sesion_id=sesion_uuid)
                if not encuesta_obj.es_anonima: resp.colaborador = perfil
                if pregunta.tipo == 'CERRADA': resp.valor_si_no = (valor == 'SI')
                else: resp.valor_texto = valor
                resp.save()
        return render(request, 'intranet/encuesta_exito.html')
    return render(request, 'intranet/encuestas_personal.html', {'encuestas': Encuesta.objects.filter(activa=True).order_by('-fecha_creacion')})

@login_required(login_url='login')
@solo_directivos
def encuestas_admin(request):
    if request.method == 'POST':
        if 'crear_encuesta' in request.POST:
            Encuesta.objects.create(titulo=request.POST.get('titulo'), descripcion=request.POST.get('descripcion'), es_anonima=request.POST.get('es_anonima') == '1', con_puntaje=request.POST.get('con_puntaje') == '1')
        elif 'crear_pregunta' in request.POST:
            enc_inst = get_object_or_404(Encuesta, id=request.POST.get('encuesta_id'))
            Pregunta.objects.create(encuesta=enc_inst, texto=request.POST.get('texto'), tipo=request.POST.get('tipo'), puntos_si=int(request.POST.get('puntos_si') or 0))
        return redirect('encuestas_admin')
    return render(request, 'intranet/encuestas_admin.html', {'encuestas': Encuesta.objects.all().prefetch_related('preguntas')})

@login_required(login_url='login')
@solo_directivos
def resultados_encuesta(request, pk):
    encuesta = get_object_or_404(Encuesta, pk=pk)
    preguntas = encuesta.preguntas.all()
    datos_graficos = []
    for p in preguntas:
        if p.tipo == 'CERRADA':
            datos_graficos.append({'id': p.id, 'texto': p.texto, 'tipo': p.tipo, 'si': p.respuestas.filter(valor_si_no=True).count(), 'no': p.respuestas.filter(valor_si_no=False).count()})
        else:
            datos_graficos.append({'id': p.id, 'texto': p.texto, 'tipo': p.tipo, 'respuestas': list(p.respuestas.exclude(valor_texto__isnull=True).exclude(valor_texto='').values_list('valor_texto', flat=True))})

    sesiones_ids = RespuestaEncuesta.objects.filter(pregunta__encuesta=encuesta).values_list('sesion_id', flat=True).distinct()
    tabla_respuestas = []
    for s_id in sesiones_ids:
        if not s_id: continue
        resp_qs = RespuestaEncuesta.objects.filter(sesion_id=s_id).select_related('colaborador__user')
        if not resp_qs.exists(): continue
        primera = resp_qs.first()
        usuario = "Anónimo" if encuesta.es_anonima else f"{primera.colaborador.user.last_name}, {primera.colaborador.user.first_name}" if primera.colaborador else "Desconocido"
        fila = {'fecha': primera.fecha_respuesta, 'usuario': usuario, 'respuestas': {}}
        for r in resp_qs: fila['respuestas'][r.pregunta_id] = "Sí" if r.valor_si_no is True else "No" if r.valor_si_no is False else r.valor_texto
        tabla_respuestas.append(fila)

    return render(request, 'intranet/encuesta_resultados.html', {'encuesta': encuesta, 'preguntas': preguntas, 'datos_graficos': datos_graficos, 'tabla_respuestas': tabla_respuestas})

@login_required(login_url='login')
@solo_directivos
def exportar_encuesta(request, pk):
    encuesta = get_object_or_404(Encuesta, pk=pk)
    preguntas = encuesta.preguntas.order_by('id')
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Resultados"
    ws.append(['Fecha de Envío', 'Colaborador'] + [p.texto for p in preguntas])
    
    for s_id in RespuestaEncuesta.objects.filter(pregunta__encuesta=encuesta).values_list('sesion_id', flat=True).distinct():
        if not s_id: continue
        resp_qs = RespuestaEncuesta.objects.filter(sesion_id=s_id)
        primera = resp_qs.first()
        row = [primera.fecha_respuesta.strftime('%Y-%m-%d %H:%M:%S'), "Anónimo" if encuesta.es_anonima else f"{primera.colaborador.user.last_name}, {primera.colaborador.user.first_name}" if primera.colaborador else "Desconocido"]
        resp_dict = {r.pregunta_id: ("Sí" if r.valor_si_no is True else "No" if r.valor_si_no is False else r.valor_texto) for r in resp_qs}
        for p in preguntas: row.append(resp_dict.get(p.id, ""))
        ws.append(row)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="Resultados_{encuesta.titulo}.xlsx"'
    wb.save(response)
    return response

# ==========================================
# COMUNICACIÓN Y HERRAMIENTAS ADICIONALES
# ==========================================
@login_required(login_url='login')
def mensajeria(request):
    perfil = getattr(request.user, 'perfil', None)
    if not perfil: return HttpResponse("Acceso Denegado: Debes tener un perfil de trabajador para usar el buzón.")
    if request.method == 'POST' and 'enviar_mensaje' in request.POST:
        destinatarios_ids = request.POST.getlist('destinatarios')
        for dest_id in destinatarios_ids:
            destinatario = Colaborador.objects.filter(id=dest_id).first()
            if destinatario: MensajeInterno.objects.create(remitente=perfil, destinatario=destinatario, asunto=request.POST.get('asunto', 'Sin Asunto'), cuerpo=request.POST.get('cuerpo', ''), adjunto=request.FILES.get('adjunto'))
        return redirect('mensajeria')
    query = request.GET.get('q', '').strip()
    mensajes_recibidos = MensajeInterno.objects.filter(destinatario=perfil).order_by('-fecha_envio')
    mensajes_enviados = MensajeInterno.objects.filter(remitente=perfil).order_by('-fecha_envio')
    if query:
        mensajes_recibidos = mensajes_recibidos.filter(Q(remitente__user__first_name__icontains=query) | Q(remitente__user__last_name__icontains=query) | Q(asunto__icontains=query))
        mensajes_enviados = mensajes_enviados.filter(Q(destinatario__user__first_name__icontains=query) | Q(destinatario__user__last_name__icontains=query) | Q(asunto__icontains=query))
    return render(request, 'intranet/mensajeria.html', {'recibidos': mensajes_recibidos, 'enviados': mensajes_enviados, 'compañeros': Colaborador.objects.exclude(id=perfil.id).select_related('user'), 'query': query})

@login_required(login_url='login')
def leer_mensaje(request, pk):
    perfil, mensaje = getattr(request.user, 'perfil', None), get_object_or_404(MensajeInterno, pk=pk)
    if mensaje.destinatario != perfil and mensaje.remitente != perfil: return redirect('mensajeria')
    if mensaje.destinatario == perfil and not mensaje.leido: 
        mensaje.leido = True
        mensaje.save()
    return render(request, 'intranet/leer_mensaje.html', {'mensaje': mensaje, 'es_receptor': mensaje.destinatario == perfil})

@login_required(login_url='login')
def calendario(request):
    perfil = getattr(request.user, 'perfil', None)
    es_admin = request.user.is_superuser or (perfil and perfil.es_directivo)
    if request.method == 'POST' and es_admin:
        titulo, inicio_str, fin_str = request.POST.get('titulo'), request.POST.get('fecha_inicio'), request.POST.get('fecha_fin')
        if titulo and inicio_str and fin_str:
            EventoCalendario.objects.create(titulo=titulo, descripcion=request.POST.get('descripcion'), fecha_inicio=datetime.strptime(inicio_str, '%Y-%m-%dT%H:%M'), fecha_fin=datetime.strptime(fin_str, '%Y-%m-%dT%H:%M'), color=request.POST.get('color', '#183D74'))
        return redirect('calendario')
    eventos_lista = [{'id': e.id, 'title': e.titulo, 'start': e.fecha_inicio.isoformat(), 'end': e.fecha_fin.isoformat(), 'description': e.descripcion or '', 'backgroundColor': e.color, 'borderColor': e.color} for e in EventoCalendario.objects.all()]
    return render(request, 'intranet/calendario.html', {'eventos_json': json.dumps(eventos_lista), 'es_admin': es_admin})

@login_required(login_url='login')
def comunicados(request): return render(request, 'intranet/comunicados.html', {'comunicados': Comunicado.objects.all().order_by('-fecha_publicacion')})

@login_required(login_url='login')
@solo_directivos
def gestor_comunicados(request):
    if request.method == 'POST':
        Comunicado.objects.create(titulo=request.POST.get('titulo'), mensaje=request.POST.get('mensaje'), adjunto=request.FILES.get('adjunto'))
        return redirect('gestor_comunicados')
    return render(request, 'intranet/gestor_comunicados.html', {'comunicados': Comunicado.objects.all().order_by('-fecha_publicacion')})

@login_required(login_url='login')
@solo_directivos
def eliminar_comunicado(request, pk): 
    get_object_or_404(Comunicado, pk=pk).delete()
    return redirect('gestor_comunicados')

@login_required(login_url='login')
@solo_directivos
def eliminar_evento(request, pk): 
    get_object_or_404(EventoCalendario, pk=pk).delete()
    return redirect('calendario')

@login_required(login_url='login')
@solo_directivos
def eliminar_candidato(request, pk): 
    get_object_or_404(CandidatoOnboarding, pk=pk).delete()
    return redirect('dashboard')

@login_required(login_url='login')
@solo_directivos
def activos(request): return render(request, 'intranet/activos.html')

@login_required(login_url='login')
@solo_directivos
def gestor_lms(request):
    from intranet.models.rrhh_core import Negocio, Colaborador # Importamos para leer carteras y roles

    if request.method == 'POST':
        # --- LÓGICA PARA CREAR UN CURSO NUEVO ---
        if 'crear_curso' in request.POST:
            titulo = request.POST.get('titulo')
            descripcion = request.POST.get('descripcion')
            tipo = request.POST.get('tipo', 'GENERAL')
            publico_general = request.POST.get('publico_general') == 'on'
            rol_permitido = request.POST.get('rol_permitido') or None
            cartera_id = request.POST.get('cartera_vinculada')

            cartera_obj = Negocio.objects.filter(id=cartera_id).first() if cartera_id else None

            CursoInduccion.objects.create(
                titulo=titulo,
                descripcion=descripcion,
                tipo=tipo,
                publico_general=publico_general,
                rol_permitido=rol_permitido,
                cartera_vinculada=cartera_obj
            )
            messages.success(request, f"¡Curso '{titulo}' creado exitosamente!")
            return redirect('gestor_lms')

        # --- LÓGICA PARA CREAR EVALUACIÓN (La que ya tenías) ---
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

    # Datos para la pantalla
    cursos_disponibles = CursoInduccion.objects.filter(activo=True)
    evaluaciones = EvaluacionCurso.objects.all().select_related('curso').prefetch_related('preguntas_balotario')
    
    # Enviamos los roles y negocios para pintar el formulario
    negocios = Negocio.objects.all()
    roles = Colaborador.ROLES

    return render(request, 'intranet/lms/gestor_lms.html', {
        'cursos': cursos_disponibles,
        'evaluaciones': evaluaciones,
        'negocios': negocios,
        'roles': roles
    })

@login_required(login_url='login')
def academia(request): return render(request, 'intranet/academia.html')

@login_required(login_url='login')
def beneficios(request): return render(request, 'intranet/beneficios.html')


# ==========================================
# MOTOR DE EXÁMENES Y BALOTARIOS (NUEVO)
# ==========================================
@login_required(login_url='login')
@solo_directivos
def importar_excel_balotario(request, evaluacion_id):
    evaluacion = get_object_or_404(EvaluacionCurso, id=evaluacion_id)

    if request.method == 'POST' and request.FILES.get('archivo_excel'):
        excel_file = request.FILES['archivo_excel']
        
        try:
            # Guardamos el archivo temporalmente
            nombre_tmp = default_storage.save(f'tmp/balotario_{request.user.id}.xlsx', ContentFile(excel_file.read()))
            wb = openpyxl.load_workbook(default_storage.open(nombre_tmp))
            
            # Sacamos las cabeceras de la primera fila
            cabeceras_excel = [str(celda.value).strip() for celda in wb.active[1] if celda.value is not None]
            
            request.session['ruta_excel_balotario'] = nombre_tmp
            request.session['evaluacion_id_temporal'] = evaluacion.id
            request.session.modified = True
            
            # Pasamos a la pantalla de mapeo
            return render(request, 'intranet/lms/mapear_balotario.html', {
                'cabeceras': cabeceras_excel,
                'evaluacion': evaluacion
            })
            
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
            from django.db import transaction # Aseguramos la importación aquí mismo por si acaso
            with transaction.atomic():
                for req_key in request.POST:
                    if req_key.startswith('enunciado_'):
                        idx = req_key.split('_')[1] 

                        nueva_pregunta = PreguntaEvaluacion.objects.create(
                            evaluacion=evaluacion,
                            enunciado=request.POST.get(f'enunciado_{idx}'),
                            puntos=request.POST.get(f'puntos_{idx}', 2.00)
                        )

                        # Guardamos la opción Correcta
                        txt_correcta = request.POST.get(f'correcta_{idx}')
                        if txt_correcta:
                            OpcionRespuesta.objects.create(pregunta=nueva_pregunta, texto=txt_correcta, es_correcta=True)
                        
                        # Guardamos las opciones Incorrectas
                        for i in range(1, 5):
                            txt_alt = request.POST.get(f'alt{i}_{idx}')
                            if txt_alt:
                                OpcionRespuesta.objects.create(pregunta=nueva_pregunta, texto=txt_alt, es_correcta=False)

            del request.session['balotario_temporal']
            del request.session['evaluacion_id_temporal']

            messages.success(request, "¡Balotario mapeado y guardado con éxito!")
            return redirect('gestor_lms')

        context = {
            'preguntas': preguntas,
            'evaluacion': evaluacion
        }
        return render(request, 'intranet/lms/previsualizar_balotario.html', context)

    except Exception as e:
        import traceback
        return HttpResponse(f"<h2>¡Atrapado en la inyección! El error real es:</h2><pre style='background:#eee; padding:20px;'>{traceback.format_exc()}</pre>")

@login_required(login_url='login')
def rendir_evaluacion(request, matricula_id):
    # 1. Identificamos al colaborador y su matrícula
    perfil = request.user.perfil
    matricula = get_object_or_404(MatriculaCurso, id=matricula_id, colaborador=perfil)
    
    # Validamos que el curso realmente tenga un examen configurado
    if not hasattr(matricula.curso, 'evaluacion'):
        messages.error(request, "Este curso aún no tiene un examen configurado.")
        return redirect('mi_induccion')
        
    evaluacion = matricula.curso.evaluacion

    # Si ya lo aprobó o lo jaló, no lo dejamos volver a darlo por esta ruta
    if matricula.estado in ['COMPLETADO', 'REPROBADO']:
        messages.info(request, f"Ya rendiste este examen. Tu nota final fue: {matricula.nota_obtenida}")
        return redirect('mi_induccion')

    # === FASE 2: EL CALIFICADOR AUTOMÁTICO (CUANDO PRESIONA "ENVIAR EXAMEN") ===
    if request.method == 'POST':
        nota_final = 0.00
        
        # Rescatamos los IDs de las preguntas exactas que le tocaron a este usuario
        preguntas_ids = request.POST.getlist('preguntas_mostradas')
        preguntas_evaluadas = PreguntaEvaluacion.objects.filter(id__in=preguntas_ids).prefetch_related('alternativas')

        # Usamos transaction.atomic para que si la luz parpadea, no se guarde un examen a medias
        with transaction.atomic():
            for pregunta in preguntas_evaluadas:
                # Vemos qué bolita (radio button) marcó el asesor
                opcion_marcada_id = request.POST.get(f'pregunta_{pregunta.id}')
                
                puntos_ganados = 0.00
                es_correcta = False
                opcion_obj = None

                if opcion_marcada_id:
                    opcion_obj = pregunta.alternativas.filter(id=opcion_marcada_id).first()
                    # Si la alternativa que marcó era la correcta, le sumamos los puntos
                    if opcion_obj and opcion_obj.es_correcta:
                        puntos_ganados = float(pregunta.puntos)
                        es_correcta = True
                        nota_final += puntos_ganados

                # Guardamos la evidencia (El registro exacto de qué marcó, útil para auditorías)
                respuesta_registro = RespuestaColaborador.objects.create(
                    matricula=matricula,
                    pregunta=pregunta,
                    es_correcta=es_correcta,
                    puntos_obtenidos=puntos_ganados
                )
                if opcion_obj:
                    respuesta_registro.opciones_marcadas.add(opcion_obj)

            # Escribimos la nota final en su matrícula
            matricula.nota_obtenida = nota_final
            matricula.fecha_finalizacion = timezone.now()
            
            # EL VEREDICTO: Comparamos contra la nota aprobatoria que fijaste
            if nota_final >= float(evaluacion.puntaje_aprobatorio):
                matricula.estado = 'COMPLETADO'
                messages.success(request, f"¡Felicidades! Has aprobado el examen con {nota_final} puntos.")
            else:
                matricula.estado = 'REPROBADO'
                messages.error(request, f"No alcanzaste la nota mínima. Obtuviste {nota_final} puntos. Deberás repasar los materiales.")
            
            matricula.save()
            return redirect('mi_induccion')

    # === FASE 1: EL REPARTIDOR (CUANDO RECIÉN ENTRA A LA PANTALLA) ===
    # Actualizamos su estado para que en el panel de RRHH se vea que está "EVALUANDO"
    if matricula.estado != 'EVALUANDO':
        matricula.estado = 'EVALUANDO'
        matricula.save()

    # EL TRUCO MAGISTRAL: Seleccionamos X preguntas al azar del balotario gigante
    if evaluacion.orden_aleatorio:
        preguntas = evaluacion.preguntas_balotario.filter(activa=True).order_by('?')[:evaluacion.preguntas_a_mostrar]
    else:
        preguntas = evaluacion.preguntas_balotario.filter(activa=True).order_by('id')[:evaluacion.preguntas_a_mostrar]

    # Mezclamos también el orden de las alternativas para que no sea siempre la "A"
    preguntas = preguntas.prefetch_related(
        Prefetch('alternativas', queryset=OpcionRespuesta.objects.order_by('?'))
    )

    return render(request, 'intranet/lms/rendir_examen.html', {
        'matricula': matricula,
        'evaluacion': evaluacion,
        'preguntas': preguntas
    })