from django.contrib import admin
from intranet.models import (
    DocumentoPersonal, CategoriaDocumento, PlantillaDocumento, 
    DocumentoGenerado, FirmaDigital
)

@admin.register(DocumentoPersonal)
class DocumentoPersonalAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'colaborador', 'tipo', 'esta_firmado', 'fecha_entrega')
    list_filter = ('tipo', 'esta_firmado')
    search_fields = ('colaborador__dni', 'colaborador__user__first_name', 'titulo')

@admin.register(CategoriaDocumento)
class CategoriaDocumentoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'requiere_firma')

@admin.register(PlantillaDocumento)
class PlantillaDocumentoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'activo', 'fecha_creacion')
    list_filter = ('activo', 'categoria')
    search_fields = ('nombre',)

@admin.register(DocumentoGenerado)
class DocumentoGeneradoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'colaborador', 'estado', 'fecha_emision')
    list_filter = ('estado', 'fecha_emision')
    search_fields = ('colaborador__first_name', 'colaborador__last_name', 'titulo')

@admin.register(FirmaDigital)
class FirmaDigitalAdmin(admin.ModelAdmin):
    list_display = ('documento', 'firmante', 'rol_firma', 'firmado', 'fecha_firma')
    list_filter = ('firmado', 'rol_firma')
    search_fields = ('firmante__first_name', 'documento__titulo')