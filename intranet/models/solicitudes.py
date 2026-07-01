from datetime import datetime
from django.db import models
from django.contrib.auth.models import User
from .rrhh_core import Colaborador

class SolicitudBase(models.Model):
    ESTADOS = [
        ('PENDIENTE_N1', 'Pendiente (Supervisor)'),
        ('PENDIENTE_N2', 'Pendiente (Sede)'),
        ('PENDIENTE_N3', 'Pendiente (RRHH)'),
        ('APROBADO', 'Aprobado'),
        ('RECHAZADO', 'Rechazado')
    ]
    
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE_N1', db_index=True)
    
    # Flujo de aprobación (Auditoría)
    aprobado_por_n1 = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='%(class)s_n1')
    fecha_n1 = models.DateTimeField(null=True, blank=True)
    
    aprobado_por_n2 = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='%(class)s_n2')
    fecha_n2 = models.DateTimeField(null=True, blank=True)
    
    aprobado_por_n3 = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='%(class)s_n3')
    fecha_n3 = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        abstract = True

    def procesar_aprobacion(self, usuario, perfil_actual, nuevo_estado, comentarios=''):
        """
        Avanza o rechaza la solicitud de forma centralizada basada en el rol del usuario que la evalúa.
        """
        if nuevo_estado == 'RECHAZADO':
            self.estado = 'RECHAZADO'
            return True

        if nuevo_estado == 'APROBADO':
            if self.estado == 'PENDIENTE_N1' and (perfil_actual.rol == 'SUPERVISOR' or perfil_actual.es_directivo):
                self.estado = 'PENDIENTE_N2'
                self.aprobado_por_n1 = usuario
                self.fecha_n1 = datetime.now()
            elif self.estado == 'PENDIENTE_N2' and (perfil_actual.rol == 'ADMINISTRATIVO' or perfil_actual.rol in ['RRHH', 'GERENCIA']):
                self.estado = 'PENDIENTE_N3'
                self.aprobado_por_n2 = usuario
                self.fecha_n2 = datetime.now()
            elif self.estado == 'PENDIENTE_N3' and perfil_actual.rol in ['RRHH', 'GERENCIA']:
                self.estado = 'APROBADO'
                self.aprobado_por_n3 = usuario
                self.fecha_n3 = datetime.now()
            else:
                # Aprobación forzada / Bypass (si un Gerente o RRHH aprueba desde N1 o N2 directo al final)
                if perfil_actual.rol in ['RRHH', 'GERENCIA']:
                    self.estado = 'APROBADO'
                    self.aprobado_por_n3 = usuario
                    self.fecha_n3 = datetime.now()
            return True
            
        return False


class Ticket(SolicitudBase):
    TIPOS = [
        ('TARDANZA', 'Justificar Tardanza'),
        ('INASISTENCIA', 'Justificar Falta'),
        ('MEDICO', 'Descanso Médico / Salud'),
        ('SOPORTE', 'Soporte TI / Otros')
    ]
    colaborador = models.ForeignKey(Colaborador, on_delete=models.CASCADE, related_name='tickets')
    tipo = models.CharField(max_length=20, choices=TIPOS, default='TARDANZA')
    motivo = models.TextField()
    adjunto_comprobante = models.FileField(upload_to='tickets_evidencias/', null=True, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True, db_index=True)
    comentarios_resolucion = models.TextField(null=True, blank=True)
    
    def procesar_aprobacion(self, usuario, perfil_actual, nuevo_estado, comentarios=''):
        resultado = super().procesar_aprobacion(usuario, perfil_actual, nuevo_estado, comentarios)
        if resultado and comentarios:
            self.comentarios_resolucion = comentarios
        return resultado


class SolicitudVacaciones(SolicitudBase):
    colaborador = models.ForeignKey(Colaborador, on_delete=models.CASCADE, related_name='vacaciones')
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    comentarios_rrhh = models.TextField(null=True, blank=True)
    fecha_solicitud = models.DateTimeField(auto_now_add=True)

    def procesar_aprobacion(self, usuario, perfil_actual, nuevo_estado, comentarios=''):
        resultado = super().procesar_aprobacion(usuario, perfil_actual, nuevo_estado, comentarios)
        if resultado and comentarios:
            self.comentarios_rrhh = comentarios
        return resultado

    @property
    def dias_solicitados(self):
        if self.fecha_inicio and self.fecha_fin:
            return (self.fecha_fin - self.fecha_inicio).days + 1
        return 0

class SaldoVacaciones(models.Model):
    colaborador = models.OneToOneField(Colaborador, on_delete=models.CASCADE, related_name='saldo_vacaciones')
    dias_asignados = models.DecimalField(max_digits=5, decimal_places=2, default=15.00, help_text="Base de días anuales (ej. 15 o 30)")
    dias_extra = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text="Días adicionales por compensación u otros")

    def __str__(self):
        return f"Saldo Vacaciones - {self.colaborador.user.get_full_name()}"

    @property
    def dias_tomados(self):
        solicitudes = self.colaborador.vacaciones.filter(estado='APROBADO')
        total = sum(s.dias_solicitados for s in solicitudes)
        return total

    @property
    def dias_disponibles(self):
        return float(self.dias_asignados + self.dias_extra) - self.dias_tomados