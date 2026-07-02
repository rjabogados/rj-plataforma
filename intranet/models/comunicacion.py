from django.db import models
from django.contrib.auth.models import User
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


class Notificacion(models.Model):
    TIPOS = [
        ('MENSAJE', 'Mensaje'),
        ('TICKET', 'Ticket'),
        ('VACACIONES', 'Vacaciones'),
        ('ALERTA', 'Alerta'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones')
    tipo = models.CharField(max_length=20, choices=TIPOS, default='ALERTA', db_index=True)
    titulo = models.CharField(max_length=180)
    detalle = models.CharField(max_length=300, blank=True, default='')
    url_destino = models.CharField(max_length=300, blank=True, default='')
    leida = models.BooleanField(default=False, db_index=True)
    creada_en = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-creada_en']

    def __str__(self):
        return f"{self.usuario.username} - {self.titulo}"

class FelicitacionCumpleaños(models.Model):
    remitente = models.ForeignKey(Colaborador, on_delete=models.CASCADE, related_name='felicitaciones_enviadas')
    destinatario = models.ForeignKey(Colaborador, on_delete=models.CASCADE, related_name='felicitaciones_recibidas')
    mensaje = models.TextField()
    fecha_envio = models.DateTimeField(auto_now_add=True)
    privado = models.BooleanField(default=False, help_text="Si es true, solo el destinatario lo ve. Si es false, aparece en el muro.")

    def __str__(self):
        return f"De {self.remitente.user.first_name} para {self.destinatario.user.first_name}"


class Reconocimiento(models.Model):
    TIPOS_MEDALLA = [
        ('ESTRELLA', 'Estrella de Desempeño 🌟'),
        ('COMPAÑERO', 'Gran Compañero 🤝'),
        ('INNOVADOR', 'Idea Innovadora 💡'),
        ('LIDERAZGO', 'Liderazgo Inspirador 👑'),
        ('SOLUCIONADOR', 'Solucionador de Problemas 🛠️'),
    ]

    emisor = models.ForeignKey(Colaborador, on_delete=models.CASCADE, related_name='reconocimientos_dados')
    receptor = models.ForeignKey(Colaborador, on_delete=models.CASCADE, related_name='reconocimientos_recibidos')
    tipo = models.CharField(max_length=50, choices=TIPOS_MEDALLA)
    mensaje = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    puntos_otorgados = models.PositiveIntegerField(default=10, help_text="Puntos sumados al receptor por este Kudo")

    def __str__(self):
        return f"{self.get_tipo_display()} para {self.receptor.user.first_name} (+{self.puntos_otorgados} pts)"

# --- CATÁLOGO Y CANJES DE PREMIOS (GAMIFICACIÓN) ---

class CatalogoPremio(models.Model):
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True, null=True)
    costo_puntos = models.PositiveIntegerField(help_text="Costo en puntos para canjear")
    stock = models.PositiveIntegerField(default=10, help_text="Cantidad disponible")
    imagen = models.ImageField(upload_to='gamificacion/premios/', null=True, blank=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} ({self.costo_puntos} pts)"

class CanjePremio(models.Model):
    ESTADOS = [
        ('PENDIENTE', 'Pendiente de Entrega'),
        ('ENTREGADO', 'Entregado'),
        ('RECHAZADO', 'Rechazado'),
    ]
    colaborador = models.ForeignKey(Colaborador, on_delete=models.CASCADE, related_name='canjes_solicitados')
    premio = models.ForeignKey(CatalogoPremio, on_delete=models.CASCADE, related_name='canjes')
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Canje de {self.colaborador.user.first_name} - {self.premio.nombre} ({self.estado})"