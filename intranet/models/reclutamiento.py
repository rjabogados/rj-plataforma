from django.db import models

class CandidatoReclutamiento(models.Model):
    # Flexibilizado para la Mini-IA (permite vacíos sin romper la base de datos)
    documento = models.CharField(max_length=20, null=True, blank=True, verbose_name="DNI/CE")
    nombre = models.CharField(max_length=150)
    telefono = models.CharField(max_length=20)
    estado_candidato = models.CharField(max_length=50)
    sede = models.CharField(max_length=50, null=True, blank=True, default="No Asignado")
    
    # --- LOS DOS CAMPOS NUEVOS QUE FALTABAN ---
    canal = models.CharField(max_length=50, null=True, blank=True, default="Por Definir")
    observaciones = models.TextField(null=True, blank=True) 
    
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Candidato de Reclutamiento"
        verbose_name_plural = "Candidatos de Reclutamiento"

    def __str__(self):
        return f"{self.nombre} - {self.sede} ({self.estado_candidato})"