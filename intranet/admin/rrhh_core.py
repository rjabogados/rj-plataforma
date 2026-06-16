from django.contrib import admin
from intranet.models import Negocio, Colaborador, Asistencia

@admin.register(Negocio)
class NegocioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)

@admin.register(Colaborador)
class ColaboradorAdmin(admin.ModelAdmin):
    # Mostramos columnas clave en el panel
    list_display = ('get_nombre_completo', 'dni', 'rol', 'negocio', 'tipo_horario')
    # Filtros laterales
    list_filter = ('rol', 'tipo_horario', 'negocio')
    # Barra de búsqueda
    search_fields = ('dni', 'user__first_name', 'user__last_name')

    def get_nombre_completo(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    get_nombre_completo.short_description = 'Nombre'

@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = ('colaborador', 'fecha', 'f1_ingreso', 'f4_salida')
    list_filter = ('fecha',)
    search_fields = ('colaborador__dni', 'colaborador__user__first_name', 'colaborador__user__last_name')