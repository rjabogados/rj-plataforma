# models/historial.py
from django.db import models
from django.utils import timezone
from .reclutamiento import CandidatoReclutamiento

class HistorialEstado(models.Model):
    """Guarda cada vez que un candidato cambia de fase (Ej: de Precalificado a Agendado)"""
    candidato = models.ForeignKey(CandidatoReclutamiento, on_delete=models.CASCADE, related_name='historial_estados')
    estado_anterior = models.CharField(max_length=50)
    estado_nuevo = models.CharField(max_length=50)
    fecha_cambio = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.candidato.nombre} -> {self.estado_nuevo}"


class RegistroContacto(models.Model):
    """Auditoría de llamadas o mensajes por parte de los asesores"""
    TIPOS_CONTACTO = [
        ('Llamada', 'Llamada'),
        ('WhatsApp', 'WhatsApp'),
        ('Correo', 'Correo'),
    ]

    candidato = models.ForeignKey(CandidatoReclutamiento, on_delete=models.CASCADE, related_name='contactos')
    asesor = models.CharField(max_length=100) # Ej. Pierina, Beatriz
    tipo = models.CharField(max_length=20, choices=TIPOS_CONTACTO)
    detalle = models.TextField(help_text="¿Qué se conversó con el candidato?")
    fecha_contacto = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.asesor} contactó a {self.candidato.nombre} via {self.tipo}"