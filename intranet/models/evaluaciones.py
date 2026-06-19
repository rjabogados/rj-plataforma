from django.db import models
from django.contrib.auth.models import User

class Examen(models.Model):
    titulo = models.CharField(max_length=200, verbose_name="Título del Examen")
    descripcion = models.TextField(blank=True, verbose_name="Descripción o Instrucciones")
    duracion_minutos = models.PositiveIntegerField(default=30, verbose_name="Duración (minutos)")
    nota_aprobacion = models.DecimalField(max_digits=4, decimal_places=2, default=14.00, verbose_name="Nota de Aprobación")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Examen"
        verbose_name_plural = "Exámenes"

    def __str__(self):
        return self.titulo

class PreguntaExamen(models.Model):
    examen = models.ForeignKey(Examen, on_delete=models.CASCADE, related_name='preguntas')
    texto = models.TextField(verbose_name="Enunciado de la Pregunta")
    imagen = models.ImageField(upload_to='examenes/', blank=True, null=True, verbose_name="Imagen Opcional")

    class Meta:
        verbose_name = "Pregunta de Examen"
        verbose_name_plural = "Preguntas de Examen"

    def __str__(self):
        return f"{self.examen.titulo} - {self.texto[:50]}"

class OpcionExamen(models.Model):
    pregunta = models.ForeignKey(PreguntaExamen, on_delete=models.CASCADE, related_name='opciones')
    texto = models.CharField(max_length=255, verbose_name="Texto de la Opción")
    es_correcta = models.BooleanField(default=False, verbose_name="¿Es la respuesta correcta?")

    class Meta:
        verbose_name = "Opción de Examen"
        verbose_name_plural = "Opciones de Examen"

    def __str__(self):
        return self.texto

class Intento(models.Model):
    ESTADOS = [
        ('EN_PROGRESO', 'En Progreso'),
        ('FINALIZADO', 'Finalizado'),
        ('EXPIRADO', 'Expirado'),
    ]
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='intentos_evaluacion')
    examen = models.ForeignKey(Examen, on_delete=models.CASCADE)
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(blank=True, null=True)
    score_total = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="Nota Final")
    estado = models.CharField(max_length=20, choices=ESTADOS, default='EN_PROGRESO')

    class Meta:
        verbose_name = "Intento de Examen"
        verbose_name_plural = "Intentos de Exámenes"

    def __str__(self):
        return f"{self.usuario.username} - {self.examen.titulo} ({self.score_total})"

class RespuestaUsuario(models.Model):
    intento = models.ForeignKey(Intento, on_delete=models.CASCADE, related_name='respuestas')
    pregunta = models.ForeignKey(PreguntaExamen, on_delete=models.CASCADE)
    opcion_seleccionada = models.ForeignKey(OpcionExamen, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Respuesta de Usuario"
        verbose_name_plural = "Respuestas de Usuarios"