from django.contrib import admin
from intranet.models import Ticket, SolicitudVacaciones

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('colaborador', 'tipo', 'estado', 'fecha_registro')
    list_filter = ('estado', 'tipo', 'fecha_registro')
    search_fields = ('colaborador__dni', 'colaborador__user__first_name')

@admin.register(SolicitudVacaciones)
class SolicitudVacacionesAdmin(admin.ModelAdmin):
    list_display = ('colaborador', 'fecha_inicio', 'fecha_fin', 'estado', 'dias_solicitados')
    list_filter = ('estado', 'fecha_solicitud')
    search_fields = ('colaborador__dni', 'colaborador__user__first_name')