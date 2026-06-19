from django.contrib import admin
from intranet.models.evaluaciones import Examen, PreguntaExamen, OpcionExamen, Intento, RespuestaUsuario

class OpcionInline(admin.TabularInline):
    model = OpcionExamen
    extra = 4

class PreguntaAdmin(admin.ModelAdmin):
    inlines = [OpcionInline]
    list_display = ['texto', 'examen']
    list_filter = ['examen']
    search_fields = ['texto']

class ExamenAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'duracion_minutos', 'nota_aprobacion', 'activo']
    list_filter = ['activo']
    search_fields = ['titulo']

class RespuestaUsuarioInline(admin.TabularInline):
    model = RespuestaUsuario
    extra = 0
    readonly_fields = ['pregunta', 'opcion_seleccionada']

class IntentoAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'examen', 'score_total', 'estado', 'fecha_inicio']
    list_filter = ['estado', 'examen']
    readonly_fields = ['usuario', 'examen', 'fecha_inicio', 'fecha_fin', 'score_total']
    inlines = [RespuestaUsuarioInline]

admin.site.register(Examen, ExamenAdmin)
admin.site.register(PreguntaExamen, PreguntaAdmin)
admin.site.register(Intento, IntentoAdmin)