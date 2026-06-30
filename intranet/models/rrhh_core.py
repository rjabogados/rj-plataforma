from django.db import models
from django.contrib.auth.models import User

class Negocio(models.Model):
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.nombre


class Area(models.Model):
    nombre = models.CharField(max_length=150, unique=True)
    descripcion = models.TextField(null=True, blank=True)
    activa = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class Cargo(models.Model):
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True, related_name='cargos')
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(null=True, blank=True)
    activa = models.BooleanField(default=True)

    class Meta:
        unique_together = ('area', 'nombre')

    def __str__(self):
        if self.area:
            return f"{self.nombre} - {self.area.nombre}"
        return self.nombre

class Colaborador(models.Model):
    ROLES = [
        ('ASESOR', 'Asesor'),
        ('BACKOFFICE', 'Backoffice'),
        ('CALIDAD', 'Calidad'),
        ('SUPERVISOR', 'Supervisor'),
        ('SISTEMAS', 'Sistemas'),
        ('ADMINISTRATIVO', 'Administrativo'),
        ('RRHH', 'Recursos Humanos'),
        ('GERENCIA', 'Gerencia')
    ]
    TIPO_HORARIO = [
        ('T1', 'Turno Mañana'),
        ('T2', 'Turno Tarde'),
        ('TC', 'Turno Completo'),
        ('PT', 'Part Time')
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    dni = models.CharField(max_length=20, unique=True, db_index=True, null=True, blank=True)
    rol = models.CharField(max_length=50, choices=ROLES, default='ASESOR', db_index=True)
    negocio = models.ForeignKey(Negocio, on_delete=models.SET_NULL, null=True, blank=True)
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True, related_name='colaboradores')
    cargo = models.ForeignKey(Cargo, on_delete=models.SET_NULL, null=True, blank=True, related_name='colaboradores')
    subcartera = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    tipo_horario = models.CharField(max_length=10, choices=TIPO_HORARIO, default='T1')
    
    hora_ingreso = models.TimeField(null=True, blank=True)
    hora_salida = models.TimeField(null=True, blank=True)
    fecha_ingreso = models.DateField(null=True, blank=True)
    
    sueldo_base = models.DecimalField(max_digits=10, decimal_places=2, default=1025.00)
    banco_pago = models.CharField(max_length=100, default='BCP')
    cuenta_bancaria = models.CharField(max_length=50, blank=True, null=True)
    regimen_laboral = models.CharField(max_length=50, default='Regimen General Mype')
    foto_perfil = models.ImageField(upload_to='perfiles/fotos/', null=True, blank=True)
    descripcion_perfil = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.last_name}, {self.user.first_name} ({self.get_rol_display()})"

    @property
    def es_directivo(self):
        return self.rol in ['ADMINISTRATIVO', 'RRHH', 'GERENCIA']

    @property
    def es_calidad(self):
        return self.rol in ['CALIDAD', 'SUPERVISOR', 'GERENCIA']

    @property
    def es_supervisor(self):
        return self.rol == 'SUPERVISOR'
        
    @property
    def es_operativo(self):
        return self.rol in ['ASESOR', 'BACKOFFICE']

    @property
    def scope_plataforma(self):
        if self.es_directivo:
            return 'ADMINISTRATIVO'
        if self.es_operativo:
            return 'ASESOR'
        return 'GENERAL'

    @property
    def puede_ver_filtros_cartera(self):
        return self.scope_plataforma == 'ASESOR'

    @property
    def puede_ver_gestion(self):
        return self.es_directivo or self.rol == 'GERENCIA'

    @property
    def puede_ver_calidad_panel(self):
        return self.es_calidad or self.es_directivo

    @property
    def puede_ver_reclutamiento(self):
        return self.es_directivo

    @property
    def puede_ver_panel_supervisor(self):
        return self.es_supervisor

class Asistencia(models.Model):
    colaborador = models.ForeignKey(Colaborador, on_delete=models.CASCADE, related_name='asistencias')
    fecha = models.DateField(db_index=True) 
    
    f1_ingreso = models.TimeField(null=True, blank=True)
    f2_salida_almuerzo = models.TimeField(null=True, blank=True)
    f3_retorno_almuerzo = models.TimeField(null=True, blank=True)
    f4_salida = models.TimeField(null=True, blank=True)
    f7_salida_break = models.TimeField(null=True, blank=True)
    f8_retorno_break = models.TimeField(null=True, blank=True)

    class Meta:
        unique_together = ('colaborador', 'fecha')