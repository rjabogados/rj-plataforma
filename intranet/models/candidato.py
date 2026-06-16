# models/candidato.py
from django.db import models
from django.utils import timezone

class CandidatoReclutamiento(models.Model):
    # El ID de matriz se genera solo por defecto en Django (el campo 'id'), 
    # pero podemos definir estados y sedes predeterminadas.
    
    ESTADOS_CHOICES = [
        ('Nuevo', 'Nuevo'),
        ('Contactado', 'Contactado'),
        ('Precalificado', 'Precalificado'),
        ('Entrevista agendada', 'Entrevista agendada'),
        ('No apto', 'No apto'),
        ('No interesados', 'No interesados'),
    ]

    nombre = models.CharField(max_length=200)
    documento = models.CharField(max_length=20, blank=True, null=True, help_text="Solo números. Guion si está vacío.")
    telefono = models.CharField(max_length=20)
    
    # Separación de Sede y Canal
    sede = models.CharField(max_length=50, null=True, blank=True, default="No Asignado")
    canal = models.CharField(max_length=100, null=True, blank=True, default='Meta Ads')
    
    estado_candidato = models.CharField(max_length=50, choices=ESTADOS_CHOICES, default='Nuevo')
    
    # Observaciones generales que se editan en el modal
    observaciones = models.TextField(blank=True, null=True)
    
    fecha_registro = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"M-{self.id:05d} | {self.nombre}"