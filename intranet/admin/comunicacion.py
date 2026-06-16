from django.contrib import admin
from intranet.models import Comunicado, MensajeInterno, EventoCalendario

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