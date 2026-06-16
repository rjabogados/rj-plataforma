from django.db import models
from .rrhh_core import Colaborador, Negocio

# --- ACADEMIA Y CURSOS ---
class CursoInduccion(models.Model):
    TIPOS_CURSO = [
        ('GENERAL', 'Cultura General RJ (Para todos)'),
        ('CARTERA', 'Específico por Cartera / Negocio'),
        ('HABILIDADES', 'Desarrollo de Habilidades (Opcional/Secundario)'),
    ]
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(help_text="Resumen de lo que el asesor aprenderá aquí.")
    tipo = models.CharField(max_length=20, choices=TIPOS_CURSO, default='GENERAL')
    cartera_vinculada = models.ForeignKey(Negocio, on_delete=models.CASCADE, null=True, blank=True)
    portada = models.ImageField(upload_to='lms_portadas/', null=True, blank=True)
    activo = models.BooleanField(default=True, db_index=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.get_tipo_display()}] {self.titulo}"

class MaterialFormativo(models.Model):
    TIPOS_MATERIAL = [
        ('VIDEO_MP4', 'Video Subido (MP4)'),
        ('YOUTUBE', 'Video Externo (YouTube/Vimeo)'),
        ('DOCUMENTO', 'PDF / Word / Diapositivas PPT'),
        ('TEXTO', 'Artículo / Políticas en Texto Rico'),
    ]
    curso = models.ForeignKey(CursoInduccion, on_delete=models.CASCADE, related_name='materiales')
    titulo = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=TIPOS_MATERIAL)
    orden = models.PositiveIntegerField(default=1)
    archivo_adjunto = models.FileField(upload_to='lms_materiales/', null=True, blank=True)
    url_externa = models.URLField(null=True, blank=True)
    contenido_texto = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['orden']

    def __str__(self):
        return f"{self.orden}. {self.titulo}"

class EvaluacionCurso(models.Model):
    curso = models.OneToOneField(CursoInduccion, on_delete=models.CASCADE, related_name='evaluacion')
    titulo = models.CharField(max_length=200, default="Examen de Conocimientos")
    instrucciones = models.TextField(blank=True)
    puntaje_aprobatorio = models.IntegerField(default=14)
    
    def __str__(self):
        return f"Evaluación: {self.curso.titulo}"

class PreguntaEvaluacion(models.Model):
    TIPOS_PREGUNTA = [
        ('ABIERTA', 'Respuesta Abierta (Desarrollo)'),
        ('MULTIPLE', 'Opción Múltiple (Una correcta)'),
        ('CASILLAS', 'Casillas (Varias correctas)'),
        ('ORDENAR', 'Ordenar Pasos Lógicos'),
        ('RELACIONAR', 'Relacionar Conceptos'),
    ]
    evaluacion = models.ForeignKey(EvaluacionCurso, on_delete=models.CASCADE, related_name='preguntas')
    enunciado = models.TextField()
    tipo = models.CharField(max_length=20, choices=TIPOS_PREGUNTA)
    imagen_apoyo = models.ImageField(upload_to='lms_preguntas/', null=True, blank=True)
    puntos = models.IntegerField(default=1)
    orden = models.PositiveIntegerField(default=1)
    configuracion_json = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['orden']

class MatriculaCurso(models.Model):
    ESTADOS = [
        ('PENDIENTE', 'Pendiente de Iniciar'),
        ('EN_CURSO', 'Viendo Materiales'),
        ('EVALUANDO', 'Rindiendo Examen'),
        ('COMPLETADO', 'Aprobado y Finalizado'),
        ('REPROBADO', 'Examen Reprobado (Requiere Reintento)')
    ]
    colaborador = models.ForeignKey(Colaborador, on_delete=models.CASCADE, related_name='cursos_matriculados')
    curso = models.ForeignKey(CursoInduccion, on_delete=models.CASCADE)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE', db_index=True)
    materiales_vistos = models.ManyToManyField(MaterialFormativo, blank=True)
    nota_obtenida = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    fecha_finalizacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('colaborador', 'curso')

class RespuestaColaborador(models.Model):
    matricula = models.ForeignKey(MatriculaCurso, on_delete=models.CASCADE, related_name='respuestas')
    pregunta = models.ForeignKey(PreguntaEvaluacion, on_delete=models.CASCADE)
    respuesta_json = models.JSONField(default=dict)
    es_correcta = models.BooleanField(default=False)
    puntos_obtenidos = models.IntegerField(default=0)
    fecha_respuesta = models.DateTimeField(auto_now_add=True)

# --- ENCUESTAS ---
class Encuesta(models.Model):
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    es_anonima = models.BooleanField(default=True)
    con_puntaje = models.BooleanField(default=False)
    activa = models.BooleanField(default=True, db_index=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titulo

class Pregunta(models.Model):
    TIPOS_PREGUNTA = [
        ('ABIERTA', 'Pregunta Abierta (Texto Libre)'),
        ('CERRADA', 'Pregunta Cerrada (Opciones Sí / No)')
    ]
    encuesta = models.ForeignKey(Encuesta, on_delete=models.CASCADE, related_name='preguntas')
    texto = models.CharField(max_length=300)
    tipo = models.CharField(max_length=20, choices=TIPOS_PREGUNTA, default='ABIERTA')
    puntos_si = models.IntegerField(default=0)

class RespuestaEncuesta(models.Model):
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE, related_name='respuestas')
    colaborador = models.ForeignKey(Colaborador, on_delete=models.CASCADE, null=True, blank=True)
    sesion_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    valor_texto = models.TextField(blank=True, null=True)
    valor_si_no = models.BooleanField(null=True, blank=True)
    fecha_respuesta = models.DateTimeField(auto_now_add=True)

# --- ONBOARDING Y RECLUTAMIENTO ---
class CandidatoOnboarding(models.Model):
    ESTADOS = (
        ('EN_PROCESO', 'En Proceso de Inducción'),
        ('COMPLETADO', 'Inducción Completada / En Planilla'),
    )
    colaborador = models.OneToOneField(Colaborador, on_delete=models.CASCADE, null=True, blank=True, related_name='onboarding_progreso')
    nombres = models.CharField(max_length=100, blank=True)
    apellidos = models.CharField(max_length=100, blank=True)
    dni = models.CharField(max_length=8, unique=True, db_index=True)
    correo = models.EmailField(blank=True, null=True)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    
    puesto_esperado = models.CharField(max_length=100, default='ASESOR')
    campaña_destino = models.ForeignKey(Negocio, on_delete=models.SET_NULL, null=True, blank=True)
    
    doc_cv = models.BooleanField(default=False)
    doc_dni = models.BooleanField(default=False)
    doc_antecedentes = models.BooleanField(default=False)
    doc_recibo_servicios = models.BooleanField(default=False)
    
    estado = models.CharField(max_length=20, choices=ESTADOS, default='EN_PROCESO', db_index=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Candidato Onboarding"
        verbose_name_plural = "Candidatos Onboarding"
        ordering = ['-fecha_registro']

    def porcentaje_expediente(self):
        docs = [self.doc_cv, self.doc_dni, self.doc_antecedentes, self.doc_recibo_servicios]
        if not docs: return 0
        return int((sum(docs) / len(docs)) * 100)