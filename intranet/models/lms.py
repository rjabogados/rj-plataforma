from django.db import models
from .rrhh_core import Colaborador, Negocio, Area, Cargo


class CategoriaModuloLMS(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    descripcion = models.CharField(max_length=220, blank=True, default='')
    icono = models.CharField(max_length=40, blank=True, default='bi-grid-1x2-fill')
    color = models.CharField(max_length=7, blank=True, default='#183D74')
    activa = models.BooleanField(default=True, db_index=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

# ==========================================
# 1. ACADEMIA Y CURSOS (AHORA CON SMART TARGETING)
# ==========================================
class CursoInduccion(models.Model):
    TIPOS_CURSO = [
        ('GENERAL', 'Cultura General RJ (Para todos)'),
        ('CARTERA', 'Específico por Cartera / Negocio'),
        ('HABILIDADES', 'Desarrollo de Habilidades (Opcional/Secundario)'),
        ('INDUCCION', 'Módulo de Onboarding / Inducción'),
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

    area_permitida = models.ForeignKey(
        Area, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='cursos_permitidos',
        help_text="Mostrar SOLO a esta área."
    )

    cargo_permitido = models.ForeignKey(
        Cargo, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='cursos_permitidos',
        help_text="Mostrar SOLO a este cargo."
    )
    
    cartera_vinculada = models.ForeignKey(
        Negocio, on_delete=models.CASCADE, null=True, blank=True, 
        help_text="Mostrar SOLO a esta Cartera/Campaña."
    )
    
    # NUEVO: Filtro quirúrgico para sub-equipos o categoría textual del curso
    subcartera_vinculada = models.CharField(
        max_length=100, null=True, blank=True,
        help_text="Para Academia: aquí se guarda la categoría del curso. Para Inducción: aquí se guarda la subcartera." 
    )

    CATEGORIAS_LMS = [
        ('Operaciones', 'Operaciones'),
        ('Ventas', 'Ventas'),
        ('Cultura RJ', 'Cultura RJ'),
        ('Servicio al Cliente', 'Servicio al Cliente'),
        ('Cumplimiento', 'Cumplimiento'),
    ]

    NIVELES_CURSO = [
        ('BASICO', 'Basico'),
        ('INTERMEDIO', 'Intermedio'),
        ('AVANZADO', 'Avanzado'),
    ]

    categoria_lms = models.ForeignKey(
        CategoriaModuloLMS,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cursos',
    )
    prerequisito_curso = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='cursos_dependientes'
    )
    modulo_padre = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='cursos_hijos'
    )
    nivel = models.CharField(max_length=20, choices=NIVELES_CURSO, default='BASICO')
    duracion_estimada_horas = models.PositiveIntegerField(default=1)
    orden_sugerido = models.PositiveIntegerField(default=1)
    obligatorio = models.BooleanField(default=False)
    certificado_habilitado = models.BooleanField(default=True)
    version = models.PositiveIntegerField(default=1)
    curso_origen = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='versiones')
    estado_publicacion = models.CharField(
        max_length=20,
        choices=[('BORRADOR', 'Borrador'), ('PUBLICADO', 'Publicado'), ('ARCHIVADO', 'Archivado')],
        default='PUBLICADO',
        db_index=True,
    )

    @property
    def categoria(self):
        return self.subcartera_vinculada

    @categoria.setter
    def categoria(self, value):
        self.subcartera_vinculada = value

    # ==========================================================

    # === CONFIGURACIÓN AVANZADA Y GAMIFICACIÓN ===
    portada = models.ImageField(upload_to='lms_portadas/', null=True, blank=True)
    # Nota: estos campos no existen en el esquema de la base de datos actual.
    # Se mantienen solo en la UI si se requiere, pero no son parte del modelo físico.
    # ==========================================================

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
    
    # Soporte nativo para presentaciones inmersivas
    url_presentacion_canva = models.URLField(
        blank=True, null=True, 
        help_text="Pega aquí el enlace de 'Ver públicamente' o 'Insertar' de Canva, Genially o Google Slides."
    )
    url_simulador = models.URLField(blank=True, null=True, help_text="URL de simulador o laboratorio práctico")
    paquete_scorm_url = models.URLField(blank=True, null=True, help_text="URL del paquete SCORM u objeto interactivo")
    
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
    intentos_maximos = models.PositiveIntegerField(default=1, help_text="0 permite intentos ilimitados")
    mostrar_resultado_inmediato = models.BooleanField(default=True)
    permitir_revision_respuestas = models.BooleanField(default=False)
    retroalimentacion_final = models.TextField(blank=True, default='')
    
    def __str__(self):
        return f"Evaluación: {self.curso.titulo}"

class PreguntaEvaluacion(models.Model):
    DIFICULTADES = [
        ('BASICO', 'Basico'),
        ('INTERMEDIO', 'Intermedio'),
        ('AVANZADO', 'Avanzado'),
    ]

    evaluacion = models.ForeignKey(EvaluacionCurso, on_delete=models.CASCADE, related_name='preguntas_balotario')
    enunciado = models.TextField()
    imagen_apoyo = models.ImageField(upload_to='lms_preguntas/', null=True, blank=True)
    tema = models.CharField(max_length=120, blank=True, default='General')
    dificultad = models.CharField(max_length=20, choices=DIFICULTADES, default='BASICO', db_index=True)
    
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
    intentos_realizados = models.PositiveIntegerField(default=0)
    fecha_limite = models.DateField(null=True, blank=True)
    certificado_codigo = models.CharField(max_length=40, unique=True, null=True, blank=True, db_index=True)
    certificado_emitido_en = models.DateTimeField(null=True, blank=True)
    certificado_vigente_hasta = models.DateField(null=True, blank=True)

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
# 4. ENCUESTAS
# ==========================================
class Encuesta(models.Model):
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    es_anonima = models.BooleanField(default=True)
    con_puntaje = models.BooleanField(default=False)
    publico_general = models.BooleanField(default=True, help_text="Si está activo, todos podrán verla.")
    rol_permitido = models.CharField(max_length=50, choices=Colaborador.ROLES, null=True, blank=True)
    area_permitida = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True, related_name='encuestas_permitidas')
    cargo_permitido = models.ForeignKey(Cargo, on_delete=models.SET_NULL, null=True, blank=True, related_name='encuestas_permitidas')
    cartera_vinculada = models.ForeignKey(Negocio, on_delete=models.SET_NULL, null=True, blank=True, related_name='encuestas_permitidas')
    subcartera_vinculada = models.CharField(max_length=100, blank=True, null=True)
    activa = models.BooleanField(default=True, db_index=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titulo

class Pregunta(models.Model):
    TIPOS_PREGUNTA = [
        ('ABIERTA', 'Pregunta Abierta (Texto Libre)'),
        ('CERRADA', 'Pregunta Cerrada (Opciones Sí / No)'),
        ('OPCION_UNICA', 'Opción Única (Lista de Alternativas)'),
        ('ESCALA_1_5', 'Escala 1 a 5'),
        ('FECHA', 'Fecha'),
    ]
    encuesta = models.ForeignKey(Encuesta, on_delete=models.CASCADE, related_name='preguntas')
    texto = models.CharField(max_length=300)
    descripcion_ayuda = models.CharField(max_length=220, blank=True, default='')
    tipo = models.CharField(max_length=20, choices=TIPOS_PREGUNTA, default='ABIERTA')
    puntos_si = models.IntegerField(default=0)
    obligatoria = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=1)
    depende_de = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='preguntas_condicionales')
    valor_disparador = models.CharField(max_length=120, blank=True, default='')

    class Meta:
        ordering = ['orden', 'id']


class OpcionPregunta(models.Model):
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE, related_name='opciones')
    texto = models.CharField(max_length=180)
    orden = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['orden', 'id']

    def __str__(self):
        return self.texto

class RespuestaEncuesta(models.Model):
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE, related_name='respuestas')
    colaborador = models.ForeignKey(Colaborador, on_delete=models.CASCADE, null=True, blank=True)
    sesion_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    valor_texto = models.TextField(blank=True, null=True)
    valor_si_no = models.BooleanField(null=True, blank=True)
    valor_opcion = models.ForeignKey(OpcionPregunta, on_delete=models.SET_NULL, null=True, blank=True, related_name='respuestas')
    valor_numero = models.IntegerField(null=True, blank=True)
    valor_fecha = models.DateField(null=True, blank=True)
    fecha_respuesta = models.DateTimeField(auto_now_add=True)


class RutaInduccion(models.Model):
    nombre = models.CharField(max_length=180)
    descripcion = models.TextField(blank=True, default='')
    rol_objetivo = models.CharField(max_length=50, choices=Colaborador.ROLES, null=True, blank=True)
    cartera_objetivo = models.ForeignKey(Negocio, on_delete=models.SET_NULL, null=True, blank=True, related_name='rutas_induccion')
    subcartera_objetivo = models.CharField(max_length=100, null=True, blank=True)
    area_objetivo = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True, related_name='rutas_induccion')
    activa = models.BooleanField(default=True, db_index=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class RutaInduccionModulo(models.Model):
    ruta = models.ForeignKey(RutaInduccion, on_delete=models.CASCADE, related_name='items')
    modulo = models.ForeignKey(CursoInduccion, on_delete=models.CASCADE, related_name='rutas_induccion')
    orden = models.PositiveIntegerField(default=1)
    prerequisito = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='desbloquea')

    class Meta:
        ordering = ['orden']
        unique_together = ('ruta', 'modulo')

    def __str__(self):
        return f"{self.ruta.nombre} - {self.modulo.titulo}"

# ==========================================
# 5. ONBOARDING Y RECLUTAMIENTO
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