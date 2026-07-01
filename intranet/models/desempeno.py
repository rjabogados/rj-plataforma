from django.db import models
from .rrhh_core import Colaborador

class PeriodoEvaluacion(models.Model):
    nombre = models.CharField(max_length=150, help_text="Ej: Evaluación Anual 2026, Q3 2026")
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

    class Meta:
        ordering = ['-fecha_inicio']

class KPI(models.Model):
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True, null=True)
    meta_default = models.DecimalField(max_digits=5, decimal_places=2, default=100.00, help_text="Meta esperada por defecto (ej. 100%)")

    def __str__(self):
        return self.nombre

class EvaluacionDesempeno(models.Model):
    ESTADOS = [
        ('PENDIENTE', 'Pendiente de Evaluación'),
        ('AUTOEVALUADO', 'Autoevaluado por el Colaborador'),
        ('EVALUADO', 'Evaluado por el Supervisor'),
        ('CERRADO', 'Evaluación Cerrada')
    ]

    NIVELES_POTENCIAL = [
        ('BAJO', 'Bajo Potencial'),
        ('MEDIO', 'Medio Potencial'),
        ('ALTO', 'Alto Potencial')
    ]

    periodo = models.ForeignKey(PeriodoEvaluacion, on_delete=models.CASCADE, related_name='evaluaciones')
    colaborador = models.ForeignKey(Colaborador, on_delete=models.CASCADE, related_name='evaluaciones_recibidas')
    evaluador = models.ForeignKey(Colaborador, on_delete=models.SET_NULL, null=True, related_name='evaluaciones_realizadas')
    
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    nota_final = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Promedio ponderado de 0 a 100")
    potencial = models.CharField(max_length=10, choices=NIVELES_POTENCIAL, null=True, blank=True, help_text="Potencial para la Matriz 9-Box")
    
    feedback_supervisor = models.TextField(blank=True, null=True, help_text="Comentarios generales del supervisor")
    autoevaluacion_comentario = models.TextField(blank=True, null=True, help_text="Comentarios del colaborador")
    
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('periodo', 'colaborador')

    def __str__(self):
        return f"{self.colaborador.user.get_full_name()} - {self.periodo.nombre}"
    
    @property
    def cuadrante_9box(self):
        if self.nota_final is None or not self.potencial:
            return "Sin datos"
        
        # Desempeño
        if self.nota_final < 60:
            desempeno_nivel = 'BAJO'
        elif self.nota_final <= 85:
            desempeno_nivel = 'MEDIO'
        else:
            desempeno_nivel = 'ALTO'
        
        potencial_nivel = self.potencial

        # Matriz 9-Box
        matriz = {
            ('BAJO', 'BAJO'): 'Riesgo / Bajo Desempeño',
            ('BAJO', 'MEDIO'): 'Inconsistente',
            ('BAJO', 'ALTO'): 'Enigma / Diamante en Bruto',
            ('MEDIO', 'BAJO'): 'Efectivo / Profesional Sólido',
            ('MEDIO', 'MEDIO'): 'Colaborador Clave',
            ('MEDIO', 'ALTO'): 'Alto Potencial',
            ('ALTO', 'BAJO'): 'Profesional Experto',
            ('ALTO', 'MEDIO'): 'Estrella Actual',
            ('ALTO', 'ALTO'): 'Futuro Líder / Superestrella',
        }
        
        return matriz.get((desempeno_nivel, potencial_nivel), "Desconocido")

class DetalleEvaluacion(models.Model):
    evaluacion = models.ForeignKey(EvaluacionDesempeno, on_delete=models.CASCADE, related_name='detalles')
    kpi = models.ForeignKey(KPI, on_delete=models.CASCADE)
    meta = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    resultado_real = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    puntuacion = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Porcentaje de cumplimiento de la meta (0-100+)")
    comentario = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('evaluacion', 'kpi')

    def __str__(self):
        return f"{self.kpi.nombre} - {self.evaluacion}"

    def calcular_puntuacion(self):
        if self.meta and self.resultado_real is not None:
            if self.meta > 0:
                self.puntuacion = (self.resultado_real / self.meta) * 100
            else:
                self.puntuacion = 0
        return self.puntuacion
