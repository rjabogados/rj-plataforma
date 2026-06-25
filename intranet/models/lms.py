from django.db import models
from .rrhh_core import Colaborador, Negocio

# ==========================================
# 1. ACADEMIA Y CURSOS (AHORA CON SMART TARGETING)
# ==========================================
class CursoInduccion(models.Model):
    TIPOS_CURSO = [
        ('GENERAL', 'Cultura General RJ (Para todos)'),
        ('CARTERA', 'Específico por Cartera / Negocio'),
        ('HABILIDADES', 'Desarrollo de Habilidades (Opcional/Secundario)'),
        ('INDUCCION', 'Módulo de Onboarding / Inducción'), # <-- Añadido explícitamente
    ]
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(help_text="Resumen de lo que el asesor aprenderá aquí.")
    tipo = models.CharField(max_length=20, choices=TIPOS_CURSO, default='GENERAL')
    
    # === REGLAS DE VISIBILIDAD INTELIGENTE (SMART TARGETING) ===
    publico_general = models.BooleanField(default=True, help_text="Si está activo, TODOS los empleados lo verán.")
    
    rol_permitido = models.CharField(
        max_length=50, choices=Colaborador.ROLES, null=True, blank=True, 
        help_text="Mostrar SOLO a este Rol (Ej: Solo Supervisores)."
    )
    
    cartera_vinculada = models.ForeignKey(
        Negocio, on_delete=models.CASCADE, null=True, blank=True, 
        help_text="Mostrar SOLO a esta Cartera/Campaña."
    )
    
    # NUEVO: Filtro quirúrgico para sub-equipos
    subcartera_vinculada = models.CharField(
        max_length=100, null=True, blank=True, 
        help_text="Ej: 'Mora Temprana' o 'Castigada'. Déjalo en blanco si es para toda la cartera."
    )
    # ==========================================================

    portada = models.ImageField(upload_to='lms_portadas/', null=True, blank=True)
    activo = models.BooleanField(default=True, db_index=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.get_tipo_display()}] {self.titulo}"

# --- MODELOS PARA CLASES Y PRESENTACIONES INTERACTIVAS ---
class LeccionCurso(models.Model):
    curso = models.ForeignKey(CursoInduccion, on_delete=models.CASCADE, related_name='lecciones')
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    
    # Soportes Multimedia
    url_video = models.URLField(blank=True, null=True, help_text="URL del video (Ej: YouTube embed)")
    archivo_pdf = models.FileField(upload_to='lms_materiales/', blank=True, null=True)
    
    # NUEVO: Soporte nativo para presentaciones inmersivas
    url_presentacion_canva = models.URLField(
        blank=True, null=True, 
        help_text="Pega aquí el enlace de 'Ver públicamente' o 'Insertar' de Canva, Genially o Google Slides."
    )
    
    orden = models.IntegerField(default=1, help_text="Orden en el que aparece la lección")

    def __str__(self):
        return f"{self.orden}. {self.titulo}"

class ProgresoLeccion(models.Model):
    colaborador = models.ForeignKey(Colaborador, on_delete=models.CASCADE)
    leccion = models.ForeignKey(LeccionCurso, on_delete=models.CASCADE)
    completada = models.BooleanField(default=False)
    fecha_completada = models.DateTimeField(auto_now_add=True)
# -----------------------------------------------
    
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

# ==========================================
# 2. MOTOR DE EXÁMENES
# ==========================================
class EvaluacionCurso(models.Model):
    curso = models.OneToOneField(CursoInduccion, on_delete=models.CASCADE, related_name='evaluacion')
    titulo = models.CharField(max_length=200, default="Examen de Conocimientos")
    instrucciones = models.TextField(blank=True)
    
    activa = models.BooleanField(default=True, help_text="Permite ocultar el examen temporalmente")
    
    # Configuraciones Dinámicas para el Balotario
    puntaje_maximo = models.DecimalField(max_digits=5, decimal_places=2, default=20.00)
    puntaje_aprobatorio = models.DecimalField(max_digits=5, decimal_places=2, default=14.00)
    
    preguntas_a_mostrar = models.PositiveIntegerField(default=10, help_text="Ej: Mostrar solo 10 al azar de un Excel de 100")
    orden_aleatorio = models.BooleanField(default=True, help_text="Mezclar las preguntas y alternativas")

    # GAMIFICACIÓN Y LÍMITE DE TIEMPO
    tiempo_limite_minutos = models.IntegerField(default=0, help_text="0 significa sin límite de tiempo")
    puntos_premio = models.IntegerField(default=50, help_text="Puntos que gana el asesor al aprobar")
    
    def __str__(self):
        return f"Evaluación: {self.curso.titulo}"

class PreguntaEvaluacion(models.Model):
    evaluacion = models.ForeignKey(EvaluacionCurso, on_delete=models.CASCADE, related_name='preguntas_balotario')
    enunciado = models.TextField()
    imagen_apoyo = models.ImageField(upload_to='lms_preguntas/', null=True, blank=True)
    
    puntos = models.DecimalField(max_digits=5, decimal_places=2, default=2.00)
    activa = models.BooleanField(default=True)

    def __str__(self):
        return self.enunciado[:50]

class OpcionRespuesta(models.Model):
    pregunta = models.ForeignKey(PreguntaEvaluacion, on_delete=models.CASCADE, related_name='alternativas')
    texto = models.CharField(max_length=255)
    es_correcta = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.texto} - {'Correcta' if self.es_correcta else 'Incorrecta'}"

# ==========================================
# 3. MATRÍCULAS Y SEGUIMIENTO DEL COLABORADOR
# ==========================================
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
        
    def __str__(self):
        return f"{self.colaborador} - {self.curso.titulo} ({self.estado})"

class RespuestaColaborador(models.Model):
    matricula = models.ForeignKey(MatriculaCurso, on_delete=models.CASCADE, related_name='respuestas_examen')
    pregunta = models.ForeignKey(PreguntaEvaluacion, on_delete=models.CASCADE)
    
    opciones_marcadas = models.ManyToManyField(OpcionRespuesta, blank=True)
    
    es_correcta = models.BooleanField(default=False)
    puntos_obtenidos = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    fecha_respuesta = models.DateTimeField(auto_now_add=True)

# ==========================================
# 4. ENCUESTAS (MANTENIDO INTACTO)
# ==========================================
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

# ==========================================
# 5. ONBOARDING Y RECLUTAMIENTO (MANTENIDO INTACTO)
# ==========================================
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
    
    portada = models.ImageField(upload_to='lms/portadas/', null=True, blank=True)
    categoria = models.CharField(max_length=50, choices=[
        ('OPERACIONES', 'Operaciones & Procesos'),
        ('HABILIDADES', 'Habilidades Blandas'),
        ('TECNICO', 'Conocimiento Técnico'),
        ('LIDERAZGO', 'Liderazgo & Gestión'),
        ('BIENESTAR', 'Cultura y Bienestar')
    ], default='TECNICO')
    puntos_recompensa = models.IntegerField(default=20, help_text="Puntos base por hacer el curso")
    nivel_dificultad = models.CharField(max_length=20, choices=[
        ('Introductorio', 'Introductorio'),
        ('Intermedio', 'Intermedio'),
        ('Avanzado', 'Avanzado')
    ], default='Introductorio')