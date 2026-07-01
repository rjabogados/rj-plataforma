import os
import uuid
from django.db import models
from django.contrib.auth.models import User
from .rrhh_core import Colaborador

# --- FUNCIONES DE ENRUTAMIENTO DINÁMICO ---
def ruta_dinamica_personal(instance, filename):
    # Entra a través del modelo Colaborador para llegar al Username
    username = instance.colaborador.user.username if instance.colaborador and instance.colaborador.user else "sin_usuario"
    return os.path.join('boveda_personal', f'usuario_{username}', filename)

def ruta_dinamica_pdf(instance, filename):
    # Aquí el colaborador ya es un objeto User directo
    username = instance.colaborador.username if instance.colaborador else "sin_usuario"
    return os.path.join('boveda_pdf', f'usuario_{username}', filename)
# ------------------------------------------

class DocumentoPersonal(models.Model):
    TIPOS_DOC = [
        ('CONTRATO', 'Contrato de Trabajo'),
        ('BOLETA', 'Boleta de Pago'),
        ('LIQUIDACION', 'Liquidación de Beneficios'),
        ('MEMORANDUM', 'Memorándum Interno'),
        ('OTROS', 'Otros Documentos')
    ]
    colaborador = models.ForeignKey(Colaborador, on_delete=models.CASCADE, related_name='documentos_digitales')
    tipo = models.CharField(max_length=20, choices=TIPOS_DOC, db_index=True)
    titulo = models.CharField(max_length=150)
    
    # Aplicamos la función dinámica aquí
    archivo = models.FileField(upload_to=ruta_dinamica_personal)
    
    requiere_firma = models.BooleanField(default=False)
    esta_firmado = models.BooleanField(default=False, db_index=True)
    fecha_firma = models.DateTimeField(null=True, blank=True)
    fecha_entrega = models.DateTimeField(auto_now_add=True)
    emitido_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

class CategoriaDocumento(models.Model):
    nombre = models.CharField(max_length=100)
    requiere_firma = models.BooleanField(default=True)
    
    def __str__(self):
        return self.nombre

class PlantillaDocumento(models.Model):
    nombre = models.CharField(max_length=200)
    categoria = models.ForeignKey(CategoriaDocumento, on_delete=models.SET_NULL, null=True)
    contenido_html = models.TextField(blank=True, null=True, help_text="Contenido HTML de la plantilla con variables")
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="plantillas_creadas")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)

class DocumentoGenerado(models.Model):
    ESTADOS = (
        ('BORRADOR', 'Borrador / Pre-visualización'),
        ('PENDIENTE', 'Pendiente de Firma'),
        ('COMPLETADO', 'Firmado y Cerrado'),
        ('ANULADO', 'Anulado / Rechazado'),
    )
    codigo_seguridad = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    colaborador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mis_documentos')
    plantilla_origen = models.ForeignKey(PlantillaDocumento, on_delete=models.SET_NULL, null=True, blank=True)
    titulo = models.CharField(max_length=255)
    
    # Aplicamos la función dinámica aquí
    archivo_pdf = models.FileField(upload_to=ruta_dinamica_pdf, blank=True, null=True)
    contenido_generado = models.TextField(blank=True, null=True, help_text="Contenido estático final firmado")
    
    estado = models.CharField(max_length=20, choices=ESTADOS, default='BORRADOR', db_index=True)
    visible_para_empleado = models.BooleanField(default=False)
    fecha_emision = models.DateTimeField(auto_now_add=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)

class FirmaDigital(models.Model):
    ROLES_FIRMA = (
        ('EMPLEADO', 'Colaborador'),
        ('SUPERVISOR', 'Supervisor Directo'),
        ('RRHH', 'Recursos Humanos'),
        ('LEGAL', 'Representante Legal'),
    )
    documento = models.ForeignKey(DocumentoGenerado, on_delete=models.CASCADE, related_name='firmas')
    firmante = models.ForeignKey(User, on_delete=models.CASCADE)
    rol_firma = models.CharField(max_length=20, choices=ROLES_FIRMA)
    orden = models.PositiveIntegerField(default=1)
    firmado = models.BooleanField(default=False, db_index=True)
    fecha_firma = models.DateTimeField(null=True, blank=True)
    direccion_ip = models.GenericIPAddressField(null=True, blank=True)
    token_utilizado = models.CharField(max_length=6, null=True, blank=True)

    class Meta:
        ordering = ['orden']