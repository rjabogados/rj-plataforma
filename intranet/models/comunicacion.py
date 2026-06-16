from django.db import models
from .rrhh_core import Colaborador

class Comunicado(models.Model):
    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    adjunto = models.FileField(upload_to='comunicados_media/', null=True, blank=True)
    fecha_publicacion = models.DateTimeField(auto_now_add=True, db_index=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.titulo

    @property
    def es_video(self):
        if self.adjunto:
            return str(self.adjunto.name).lower().endswith(('.mp4', '.mov', '.avi', '.webm'))
        return False

    @property
    def es_imagen(self):
        if self.adjunto:
            return str(self.adjunto.name).lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp'))
        return False

class MensajeInterno(models.Model):
    remitente = models.ForeignKey(Colaborador, on_delete=models.CASCADE, related_name='mensajes_enviados')
    destinatario = models.ForeignKey(Colaborador, on_delete=models.CASCADE, related_name='mensajes_recibidos')
    asunto = models.CharField(max_length=200, default="Sin Asunto")
    cuerpo = models.TextField()
    adjunto = models.FileField(upload_to='mensajeria_adjuntos/', null=True, blank=True)
    leido = models.BooleanField(default=False, db_index=True)
    fecha_envio = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.asunto} - De: {self.remitente.user.first_name} Para: {self.destinatario.user.first_name}"
    
class EventoCalendario(models.Model):
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    fecha_inicio = models.DateTimeField(db_index=True)
    fecha_fin = models.DateTimeField(db_index=True)
    color = models.CharField(max_length=7, default="#183D74")

    def __str__(self):
        return self.titulo