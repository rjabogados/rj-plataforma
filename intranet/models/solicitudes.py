from django.db import models
from django.contrib.auth.models import User
from .rrhh_core import Colaborador

class Ticket(models.Model):
    TIPOS = [
        ('TARDANZA', 'Justificar Tardanza'),
        ('INASISTENCIA', 'Justificar Falta'),
        ('MEDICO', 'Descanso Médico / Salud'),
        ('SOPORTE', 'Soporte TI / Otros')
    ]
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('APROBADO', 'Aprobado'),
        ('RECHAZADO', 'Rechazado')
    ]
    colaborador = models.ForeignKey(Colaborador, on_delete=models.CASCADE, related_name='tickets')
    tipo = models.CharField(max_length=20, choices=TIPOS, default='TARDANZA')
    motivo = models.TextField()
    adjunto_comprobante = models.FileField(upload_to='tickets_evidencias/', null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE', db_index=True) 
    fecha_registro = models.DateTimeField(auto_now_add=True, db_index=True)
    revisado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets_revisados')

class SolicitudVacaciones(models.Model):
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('APROBADO', 'Aprobado'),
        ('RECHAZADO', 'Rechazado')
    ]
    colaborador = models.ForeignKey(Colaborador, on_delete=models.CASCADE, related_name='vacaciones')
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=50, choices=ESTADOS, default='PENDIENTE', db_index=True)
    comentarios_rrhh = models.TextField(null=True, blank=True)
    revisado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='vacaciones_revisadas')
    fecha_solicitud = models.DateTimeField(auto_now_add=True)

    @property
    def dias_solicitados(self):
        if self.fecha_inicio and self.fecha_fin:
            return (self.fecha_fin - self.fecha_inicio).days + 1
        return 0