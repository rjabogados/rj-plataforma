import shutil
import tempfile
from datetime import date
from datetime import time
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from intranet.models import Colaborador, Comunicado, DocumentoGenerado, CursoInduccion, MatriculaCurso, MensajeInterno, Ticket, SolicitudVacaciones, Area, Cargo, Negocio, Notificacion, CategoriaModuloLMS
from intranet.models.lms import Encuesta, Pregunta, OpcionPregunta, RespuestaEncuesta, RutaInduccion, RutaInduccionModulo
from intranet.models.lms import LeccionCurso, EvaluacionCurso
from intranet.models import Asistencia
from intranet.models import CandidatoReclutamiento


TEST_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class SecurityAccessTests(TestCase):
	@classmethod
	def tearDownClass(cls):
		super().tearDownClass()
		shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

	def setUp(self):
		self.user = self.crear_usuario('empleado', 'ASESOR', '1001')
		self.other_user = self.crear_usuario('otro', 'ASESOR', '1002')
		self.directivo = self.crear_usuario('rrhh', 'RRHH', '1003')

	def crear_usuario(self, username, rol, dni):
		user = User.objects.create_user(username=username, password='test12345')
		Colaborador.objects.create(user=user, dni=dni, rol=rol)
		return user

	def crear_usuario_segmentado(self, username, rol, dni, area=None, cargo=None, negocio=None, subcartera=None):
		user = User.objects.create_user(username=username, password='test12345', first_name=username, last_name='Test')
		Colaborador.objects.create(user=user, dni=dni, rol=rol, area=area, cargo=cargo, negocio=negocio, subcartera=subcartera)
		return user

	def crear_documento(self, user, titulo='Contrato de prueba'):
		documento = DocumentoGenerado.objects.create(colaborador=user, titulo=titulo, estado='PENDIENTE')
		documento.archivo_pdf.save('prueba.pdf', ContentFile(b'%PDF-1.4 prueba'))
		return documento

	def crear_leccion_con_pdf(self):
		curso = CursoInduccion.objects.create(
			titulo='Curso seguro',
			descripcion='Contenido',
			tipo='GENERAL',
			publico_general=True,
		)
		leccion = LeccionCurso.objects.create(curso=curso, titulo='Leccion PDF', orden=1)
		leccion.archivo_pdf.save('manual.pdf', ContentFile(b'%PDF-1.4 manual'))
		return curso, leccion

	def crear_mensaje(self):
		mensaje = MensajeInterno.objects.create(
			remitente=self.directivo.perfil,
			destinatario=self.user.perfil,
			asunto='Aviso interno',
			cuerpo='Contenido de prueba',
		)
		mensaje.adjunto.save('nota.pdf', ContentFile(b'%PDF-1.4 nota'))
		return mensaje

	def crear_comunicado(self):
		comunicado = Comunicado.objects.create(titulo='Anuncio', mensaje='Mensaje general', activo=True)
		comunicado.adjunto.save('anuncio.pdf', ContentFile(b'%PDF-1.4 anuncio'))
		return comunicado

	def crear_ticket(self, colaborador):
		ticket = Ticket.objects.create(
			colaborador=colaborador.perfil,
			tipo='MEDICO',
			motivo='Sustento de prueba',
		)
		ticket.adjunto_comprobante.save('sustento.pdf', ContentFile(b'%PDF-1.4 sustento'))
		return ticket

	def crear_encuesta_segmentada(self, area=None, cargo=None, negocio=None, subcartera=None):
		encuesta = Encuesta.objects.create(
			titulo='Encuesta segmentada',
			descripcion='Prueba',
			es_anonima=True,
			con_puntaje=False,
			publico_general=False,
			area_permitida=area,
			cargo_permitido=cargo,
			cartera_vinculada=negocio,
			subcartera_vinculada=subcartera,
		)
		Pregunta.objects.create(encuesta=encuesta, texto='¿Todo bien?', tipo='ABIERTA')
		return encuesta

	def test_metricas_dashboard_requiere_login(self):
		response = self.client.get(reverse('api_metricas_dashboard'))
		self.assertEqual(response.status_code, 302)
		self.assertIn(reverse('login'), response.url)

	def test_metricas_dashboard_restringe_asesor(self):
		self.client.login(username='empleado', password='test12345')
		response = self.client.get(reverse('api_metricas_dashboard'))
		self.assertEqual(response.status_code, 403)

	def test_documento_personal_solo_para_propietario(self):
		documento = self.crear_documento(self.user)

		self.client.login(username='empleado', password='test12345')
		response = self.client.get(reverse('ver_documento_personal', args=[documento.id]))
		self.assertEqual(response.status_code, 200)

		self.client.logout()
		self.client.login(username='otro', password='test12345')
		response = self.client.get(reverse('ver_documento_personal', args=[documento.id]))
		self.assertEqual(response.status_code, 404)

	def test_leccion_pdf_solo_para_matriculados_o_directivos(self):
		curso, leccion = self.crear_leccion_con_pdf()
		MatriculaCurso.objects.create(colaborador=self.user.perfil, curso=curso)

		self.client.login(username='empleado', password='test12345')
		response = self.client.get(reverse('ver_leccion_pdf', args=[leccion.id]))
		self.assertEqual(response.status_code, 200)

		self.client.logout()
		self.client.login(username='otro', password='test12345')
		response = self.client.get(reverse('ver_leccion_pdf', args=[leccion.id]))
		self.assertEqual(response.status_code, 404)

		self.client.logout()
		self.client.login(username='rrhh', password='test12345')
		response = self.client.get(reverse('ver_leccion_pdf', args=[leccion.id]))
		self.assertEqual(response.status_code, 200)

	def test_leer_mensaje_solo_para_participantes_y_marca_leido(self):
		mensaje = self.crear_mensaje()

		self.client.login(username='empleado', password='test12345')
		response = self.client.get(reverse('leer_mensaje', args=[mensaje.id]))
		self.assertEqual(response.status_code, 200)
		mensaje.refresh_from_db()
		self.assertTrue(mensaje.leido)

		self.client.logout()
		self.client.login(username='otro', password='test12345')
		response = self.client.get(reverse('leer_mensaje', args=[mensaje.id]))
		self.assertEqual(response.status_code, 404)

	def test_adjunto_mensaje_solo_para_participantes(self):
		mensaje = self.crear_mensaje()

		self.client.login(username='empleado', password='test12345')
		response = self.client.get(reverse('ver_adjunto_mensaje', args=[mensaje.id]))
		self.assertEqual(response.status_code, 200)

		self.client.logout()
		self.client.login(username='otro', password='test12345')
		response = self.client.get(reverse('ver_adjunto_mensaje', args=[mensaje.id]))
		self.assertEqual(response.status_code, 404)

	def test_adjunto_comunicado_requiere_login(self):
		comunicado = self.crear_comunicado()

		response = self.client.get(reverse('ver_adjunto_comunicado', args=[comunicado.id]))
		self.assertEqual(response.status_code, 302)

		self.client.login(username='empleado', password='test12345')
		response = self.client.get(reverse('ver_adjunto_comunicado', args=[comunicado.id]))
		self.assertEqual(response.status_code, 200)

	def test_adjunto_ticket_solo_para_propietario_o_directivo(self):
		ticket = self.crear_ticket(self.user)

		self.client.login(username='empleado', password='test12345')
		response = self.client.get(reverse('ver_adjunto_ticket', args=[ticket.id]))
		self.assertEqual(response.status_code, 200)

		self.client.logout()
		self.client.login(username='rrhh', password='test12345')
		response = self.client.get(reverse('ver_adjunto_ticket', args=[ticket.id]))
		self.assertEqual(response.status_code, 200)

		self.client.logout()
		self.client.login(username='otro', password='test12345')
		response = self.client.get(reverse('ver_adjunto_ticket', args=[ticket.id]))
		self.assertEqual(response.status_code, 404)

	def test_revisar_ticket_requiere_post(self):
		ticket = self.crear_ticket(self.user)

		self.client.login(username='rrhh', password='test12345')
		response = self.client.get(reverse('revisar_ticket', args=[ticket.id, 'APROBADO']))
		self.assertEqual(response.status_code, 405)

		response = self.client.post(reverse('revisar_ticket', args=[ticket.id, 'APROBADO']))
		self.assertEqual(response.status_code, 302)
		ticket.refresh_from_db()
		self.assertEqual(ticket.estado, 'APROBADO')

	def test_encuestas_personal_respeta_segmentacion_por_area(self):
		area = Area.objects.create(nombre='Cobranza')
		otra_area = Area.objects.create(nombre='RRHH Interno')
		self.user.perfil.area = area
		self.user.perfil.save()
		self.other_user.perfil.area = otra_area
		self.other_user.perfil.save()

		self.crear_encuesta_segmentada(area=area)

		self.client.login(username='empleado', password='test12345')
		response = self.client.get(reverse('encuestas_personal'))
		self.assertContains(response, 'Encuesta segmentada')

		self.client.logout()
		self.client.login(username='otro', password='test12345')
		response = self.client.get(reverse('encuestas_personal'))
		self.assertNotContains(response, 'Encuesta segmentada')

	def test_tickets_admin_filtra_por_area(self):
		area = Area.objects.create(nombre='Operaciones')
		otra_area = Area.objects.create(nombre='Administración')
		asesor_operaciones = self.crear_usuario_segmentado('asesor_op', 'ASESOR', '1004', area=area)
		asesor_otro = self.crear_usuario_segmentado('asesor_otro2', 'ASESOR', '1005', area=otra_area)
		self.crear_ticket(asesor_operaciones)
		self.crear_ticket(asesor_otro)

		self.client.login(username='rrhh', password='test12345')
		response = self.client.get(reverse('tickets_admin'), {'area': area.id})
		self.assertEqual(response.status_code, 200)
		tickets_filtrados = list(response.context['tickets'])
		self.assertEqual(len(tickets_filtrados), 1)
		self.assertEqual(tickets_filtrados[0].colaborador.user.username, 'asesor_op')

	def test_dashboard_rrhh_y_export_directorio(self):
		area = Area.objects.create(nombre='Cobranza')
		cargo = Cargo.objects.create(area=area, nombre='Gestor Senior')
		negocio = Negocio.objects.create(nombre='Mora Masiva')
		perfil = self.crear_usuario_segmentado('rrhh_soporte', 'RRHH', '1006', area=area, cargo=cargo, negocio=negocio, subcartera='Temprana')
		perfil.perfil.hora_ingreso = time(9, 0)
		perfil.perfil.fecha_ingreso = date(2025, 6, 1)
		perfil.perfil.save()

		Asistencia.objects.create(colaborador=perfil.perfil, fecha=date.today(), f1_ingreso=time(9, 30))
		Asistencia.objects.create(colaborador=self.user.perfil, fecha=date.today())

		self.client.login(username='rrhh', password='test12345')

		response = self.client.get(reverse('dashboard_rrhh'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Panel RRHH')
		self.assertContains(response, 'Colaboradores')
		self.assertContains(response, 'Atrasos de Hoy')
		self.assertContains(response, 'Sin Marcación de Ingreso')
		self.assertContains(response, '+30 min')

		response = self.client.get(reverse('exportar_directorio_rrhh'))
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response['Content-Type'].startswith('text/csv'), True)
		self.assertContains(response, 'Usuario')
		self.assertContains(response, 'rrhh_soporte')

	def test_dashboard_supervisor_muestra_equipo_y_exporta(self):
		area = Area.objects.create(nombre='Operaciones Supervisadas')
		cargo = Cargo.objects.create(area=area, nombre='Supervisor Senior')
		supervisor = self.crear_usuario_segmentado('supervisor1', 'SUPERVISOR', '2001', area=area, cargo=cargo)
		miembro = self.crear_usuario_segmentado('asesor_area', 'ASESOR', '2002', area=area)
		self.crear_usuario_segmentado('asesor_fuera', 'ASESOR', '2003')
		Asistencia.objects.create(colaborador=miembro.perfil, fecha=date.today())

		self.client.login(username='supervisor1', password='test12345')

		response = self.client.get(reverse('dashboard_supervisor'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Panel Supervisor')
		self.assertContains(response, 'asesor_area')
		self.assertNotContains(response, 'asesor_fuera')

		response = self.client.get(reverse('exportar_equipo_supervisor'))
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response['Content-Type'].startswith('text/csv'), True)
		self.assertContains(response, 'Usuario')
		self.assertContains(response, 'asesor_area')
		self.assertNotContains(response, 'asesor_fuera')

	def test_perfil_admin_muestra_ficha_por_persona(self):
		area = Area.objects.create(nombre='Cobranza Detallada')
		cargo = Cargo.objects.create(area=area, nombre='Gestor Premium')
		negocio = Negocio.objects.create(nombre='Cartera Neta')
		colaborador = self.crear_usuario_segmentado('ficha_admin', 'ASESOR', '3001', area=area, cargo=cargo, negocio=negocio, subcartera='Temprana')
		colaborador.perfil.hora_ingreso = time(8, 0)
		colaborador.perfil.save()

		Asistencia.objects.create(colaborador=colaborador.perfil, fecha=date.today(), f1_ingreso=time(8, 20))
		Ticket.objects.create(colaborador=colaborador.perfil, tipo='TARDANZA', motivo='Llegó tarde por tráfico')
		SolicitudVacaciones.objects.create(colaborador=colaborador.perfil, fecha_inicio=date.today(), fecha_fin=date.today())

		self.client.login(username='rrhh', password='test12345')
		response = self.client.get(reverse('perfil_admin'), {'colaborador': colaborador.perfil.id})
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Ficha Administrativa por Persona')
		self.assertContains(response, 'ficha_admin')
		self.assertContains(response, 'Llegó tarde por tráfico')
		self.assertContains(response, 'Vacaciones')

	def test_perfil_permite_actualizar_descripcion_y_foto(self):
		self.client.login(username='empleado', password='test12345')
		foto = SimpleUploadedFile('perfil.png', b'fake-image-bytes', content_type='image/png')

		response = self.client.post(reverse('perfil'), {
			'accion': 'datos',
			'descripcion_perfil': 'Perfil actualizado desde la plataforma',
			'foto_perfil': foto,
		})

		self.assertEqual(response.status_code, 302)
		self.user.perfil.refresh_from_db()
		self.assertEqual(self.user.perfil.descripcion_perfil, 'Perfil actualizado desde la plataforma')
		self.assertTrue(self.user.perfil.foto_perfil.name.endswith('perfil.png'))

	def test_perfil_permite_cambiar_password(self):
		self.client.login(username='empleado', password='test12345')

		response = self.client.post(reverse('perfil'), {
			'accion': 'password',
			'old_password': 'test12345',
			'new_password1': 'NuevoPass12345',
			'new_password2': 'NuevoPass12345',
		})

		self.assertEqual(response.status_code, 302)
		self.assertTrue(self.client.login(username='empleado', password='NuevoPass12345'))

	def test_perfil_renderiza_sin_colaborador_asociado(self):
		admin = User.objects.create_user(username='adminbase', password='test12345', first_name='Admin', last_name='Base')

		self.client.login(username='adminbase', password='test12345')
		response = self.client.get(reverse('perfil'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Administrador')
		self.assertContains(response, 'Sin área')

	def test_colaborador_se_puede_crear_sin_dni(self):
		self.client.login(username='rrhh', password='test12345')

		response = self.client.post(reverse('colaboradores'), {
			'nombres': 'Sin',
			'apellidos': 'Documento',
			'dni': '',
			'correo': 'sin.dni@test.com',
			'rol': 'ASESOR',
			'negocio': '',
			'area': '',
			'cargo': '',
			'subcartera': '',
			'tipo_horario': 'T1',
			'hora_ingreso': '',
			'hora_salida': '',
			'fecha_ingreso': date.today().strftime('%Y-%m-%d'),
			'username': '',
			'password': '',
		})

		self.assertEqual(response.status_code, 302)
		perfil = Colaborador.objects.get(user__email='sin.dni@test.com')
		self.assertIsNone(perfil.dni)

	def test_crear_mensaje_genera_notificacion_destinatario(self):
		self.client.login(username='rrhh', password='test12345')

		response = self.client.post(reverse('mensajeria'), {
			'enviar_mensaje': '1',
			'destinatarios': [self.user.perfil.id],
			'asunto': 'Recordatorio',
			'cuerpo': 'Revisa tu tablero hoy.',
		})

		self.assertEqual(response.status_code, 302)
		notificacion = Notificacion.objects.filter(usuario=self.user, tipo='MENSAJE').first()
		self.assertIsNotNone(notificacion)
		self.assertIn('Nuevo mensaje', notificacion.titulo)

	def test_leer_notificacion_la_marca_y_redirige(self):
		notificacion = Notificacion.objects.create(
			usuario=self.directivo,
			tipo='ALERTA',
			titulo='Nueva alerta',
			detalle='Revisa pendientes.',
			url_destino='/tickets-admin/',
		)

		self.client.login(username='rrhh', password='test12345')
		response = self.client.get(reverse('leer_notificacion', args=[notificacion.id]))

		self.assertEqual(response.status_code, 302)
		self.assertIn('/tickets-admin/', response.url)
		notificacion.refresh_from_db()
		self.assertTrue(notificacion.leida)

	def test_gestor_lms_crea_categoria_dinamica(self):
		self.client.login(username='rrhh', password='test12345')

		response = self.client.post(reverse('gestor_lms'), {
			'crear_categoria_lms': '1',
			'nombre_categoria': 'Normativas Internas',
			'descripcion_categoria': 'Politicas y cumplimiento',
			'icono_categoria': 'bi-shield-check',
			'color_categoria': '#1259A6',
		})

		self.assertEqual(response.status_code, 302)
		self.assertTrue(CategoriaModuloLMS.objects.filter(nombre='Normativas Internas', activa=True).exists())

	def test_rendir_evaluacion_bloquea_cuando_alcanza_limite_intentos(self):
		curso = CursoInduccion.objects.create(titulo='Curso Límite', descripcion='Test', tipo='GENERAL')
		EvaluacionCurso.objects.create(
			curso=curso,
			titulo='Examen Límite',
			puntaje_maximo=20,
			puntaje_aprobatorio=14,
			preguntas_a_mostrar=1,
			intentos_maximos=1,
		)
		matricula = MatriculaCurso.objects.create(
			colaborador=self.user.perfil,
			curso=curso,
			estado='REPROBADO',
			intentos_realizados=1,
		)

		self.client.login(username='empleado', password='test12345')
		response = self.client.get(reverse('rendir_evaluacion', args=[matricula.id]))

		self.assertEqual(response.status_code, 302)
		self.assertIn(reverse('detalle_curso', args=[curso.id]), response.url)

	def test_encuesta_guarda_respuesta_con_usuario_logueado(self):
		encuesta = Encuesta.objects.create(titulo='Formulario interno', activa=True, publico_general=True)
		pregunta = Pregunta.objects.create(encuesta=encuesta, texto='Nivel de satisfacción', tipo='OPCION_UNICA', obligatoria=True)
		opcion = OpcionPregunta.objects.create(pregunta=pregunta, texto='Alto', orden=1)

		self.client.login(username='empleado', password='test12345')
		response = self.client.post(reverse('encuestas_personal'), {
			'enviar_encuesta': '1',
			'encuesta_id': encuesta.id,
			f'pregunta_{pregunta.id}': str(opcion.id),
		})

		self.assertEqual(response.status_code, 302)
		respuesta = RespuestaEncuesta.objects.get(pregunta=pregunta)
		self.assertEqual(respuesta.colaborador_id, self.user.perfil.id)
		self.assertEqual(respuesta.valor_opcion_id, opcion.id)

	def test_asignar_modulos_induccion_aplica_ruta(self):
		curso_1 = CursoInduccion.objects.create(titulo='Induccion 1', descripcion='Base', tipo='INDUCCION', activo=True)
		curso_2 = CursoInduccion.objects.create(titulo='Induccion 2', descripcion='Base', tipo='INDUCCION', activo=True)
		ruta = RutaInduccion.objects.create(nombre='Ruta Operativa', activa=True)
		RutaInduccionModulo.objects.create(ruta=ruta, modulo=curso_1, orden=1)
		RutaInduccionModulo.objects.create(ruta=ruta, modulo=curso_2, orden=2)

		self.client.login(username='rrhh', password='test12345')
		response = self.client.post(reverse('asignar_modulos_induccion', args=[self.user.perfil.id]), {
			'ruta_id': ruta.id,
		})

		self.assertEqual(response.status_code, 302)
		matriculas = MatriculaCurso.objects.filter(colaborador=self.user.perfil).order_by('curso__titulo')
		self.assertEqual(matriculas.count(), 2)
		self.assertTrue(all(m.fecha_limite is not None for m in matriculas))

	def test_mi_induccion_bloquea_modulo_con_prerequisito(self):
		curso_base = CursoInduccion.objects.create(
			titulo='Modulo Base', descripcion='Base', tipo='INDUCCION', activo=True, publico_general=True
		)
		curso_avanzado = CursoInduccion.objects.create(
			titulo='Modulo Avanzado', descripcion='Avanzado', tipo='INDUCCION', activo=True, publico_general=True,
			prerequisito_curso=curso_base,
		)

		self.client.login(username='empleado', password='test12345')
		response = self.client.get(reverse('mi_induccion'))
		self.assertEqual(response.status_code, 200)

		matricula_avanzado = MatriculaCurso.objects.get(colaborador=self.user.perfil, curso=curso_avanzado)
		self.assertIn(matricula_avanzado.id, response.context['bloqueados_ids'])

		matricula_base = MatriculaCurso.objects.get(colaborador=self.user.perfil, curso=curso_base)
		matricula_base.estado = 'COMPLETADO'
		matricula_base.fecha_finalizacion = timezone.now()
		matricula_base.save(update_fields=['estado', 'fecha_finalizacion'])

		response = self.client.get(reverse('mi_induccion'))
		self.assertEqual(response.status_code, 200)
		self.assertNotIn(matricula_avanzado.id, response.context['bloqueados_ids'])

	def test_duplicar_version_curso_crea_borrador_nuevo(self):
		curso = CursoInduccion.objects.create(
			titulo='LMS Ventas', descripcion='v1', tipo='ACADEMIA', version=2, estado_publicacion='PUBLICADO', activo=True
		)

		self.client.login(username='rrhh', password='test12345')
		response = self.client.get(reverse('duplicar_version_curso', args=[curso.id]))

		self.assertEqual(response.status_code, 302)
		nueva_version = CursoInduccion.objects.exclude(id=curso.id).get(titulo='LMS Ventas', version=3)
		self.assertEqual(nueva_version.estado_publicacion, 'BORRADOR')
		self.assertEqual(nueva_version.curso_origen_id, curso.id)

	def test_verificar_certificado_responde_valido_e_invalido(self):
		curso = CursoInduccion.objects.create(titulo='Certificacion QA', descripcion='QA', tipo='ACADEMIA', activo=True)
		MatriculaCurso.objects.create(
			colaborador=self.user.perfil,
			curso=curso,
			estado='COMPLETADO',
			certificado_codigo='CERT-TEST-001',
			certificado_vigente_hasta=date.today() + timedelta(days=30),
		)

		response = self.client.get(reverse('verificar_certificado', args=['CERT-TEST-001']))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Certificado válido')

		response = self.client.get(reverse('verificar_certificado', args=['NO-EXISTE']))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Certificado no encontrado')

	def test_comando_recordatorios_lms_no_duplica_notificacion_diaria(self):
		curso = CursoInduccion.objects.create(titulo='Modulo Pendiente', descripcion='Pendiente', tipo='ACADEMIA', activo=True)
		MatriculaCurso.objects.create(
			colaborador=self.user.perfil,
			curso=curso,
			estado='PENDIENTE',
			fecha_limite=date.today() - timedelta(days=1),
		)

		call_command('recordatorios_lms')
		call_command('recordatorios_lms')

		notificaciones = Notificacion.objects.filter(usuario=self.user, titulo='Recordatorio: modulo vencido')
		self.assertEqual(notificaciones.count(), 1)

	def test_limpieza_matriz_reclutamiento_consolida_duplicados(self):
		CandidatoReclutamiento.objects.create(
			documento=' 123-456 ',
			nombre='Juan   Perez',
			telefono=' 999-888-777 ',
			estado_candidato='entrevista',
			sede=' Lima ',
			canal=' Meta Ads ',
		)
		CandidatoReclutamiento.objects.create(
			documento='123456',
			nombre='Juan Perez Gomez',
			telefono='999888777',
			estado_candidato='No interesado',
			sede='LIMA',
			canal='Web',
		)

		from django.core.management import call_command
		call_command('limpiar_matriz_reclutamiento')

		self.assertEqual(CandidatoReclutamiento.objects.filter(documento='123456').count(), 1)
		candidato = CandidatoReclutamiento.objects.get(documento='123456')
		self.assertEqual(candidato.estado_candidato, 'No interesados')
		self.assertEqual(candidato.sede, 'LIMA')
		self.assertEqual(candidato.canal, 'Web')
