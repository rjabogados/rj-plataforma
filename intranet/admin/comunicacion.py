from django.contrib import admin
from intranet.models import Comunicado, MensajeInterno, EventoCalendario, CategoriaVotacion, VotoMensual

@admin.register(Comunicado)
class ComunicadoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'fecha_publicacion', 'activo')
    list_filter = ('activo', 'fecha_publicacion')
    search_fields = ('titulo',)

@admin.register(MensajeInterno)
class MensajeInternoAdmin(admin.ModelAdmin):
    list_display = ('asunto', 'remitente', 'destinatario', 'leido', 'fecha_envio')
    list_filter = ('leido', 'fecha_envio')
    search_fields = ('asunto', 'remitente__user__first_name', 'destinatario__user__first_name')

@admin.register(EventoCalendario)
class EventoCalendarioAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'fecha_inicio', 'fecha_fin', 'color')
    list_filter = ('fecha_inicio',)

@admin.register(CategoriaVotacion)
class CategoriaVotacionAdmin(admin.ModelAdmin):
    list_display = ('icono', 'nombre', 'activa')
    list_filter = ('activa',)
    search_fields = ('nombre',)

@admin.register(VotoMensual)
class VotoMensualAdmin(admin.ModelAdmin):
    list_display = ('votante', 'candidato', 'categoria', 'mes', 'anio')
    list_filter = ('mes', 'anio', 'categoria')
    search_fields = ('votante__user__first_name', 'candidato__user__first_name')