from django.contrib import admin
from intranet.models import Ticket, SolicitudVacaciones

@admin.register(Ticket)
class TicketsAdmin(admin.ModelAdmin):
    list_display = ('colaborador', 'tipo', 'estado', 'fecha_registro')
    list_filter = ('estado', 'tipo', 'fecha_registro')
    search_fields = ('colaborador__dni', 'colaborador__user__first_name')

    # 1. Filtro para que cada quien vea solo lo suyo
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Si es jefe o RRHH, ve todo
        if request.user.is_superuser or request.user.groups.filter(name__in=['Administración y RRHH', 'Supervisores de Operaciones']).exists():
            return qs
        # Si es personal base, se filtra por su usuario vinculado
        return qs.filter(colaborador__user=request.user)

    # 2. Asignación automática del autor al guardar
    def save_model(self, request, obj, form, change):
        if not change: # Solo si es un registro nuevo
            if not hasattr(obj, 'colaborador') or not obj.colaborador:
                if hasattr(request.user, 'colaborador'):
                    obj.colaborador = request.user.colaborador
        super().save_model(request, obj, form, change)

    # 3. Ocultar el campo 'colaborador' a los usuarios base para evitar que elijan a otros
    def get_form(self, request, obj=None, **kwargs):
        if not request.user.is_superuser and not request.user.groups.filter(name__in=['Administración y RRHH', 'Supervisores de Operaciones']).exists():
            self.exclude = ('colaborador',)
        else:
            self.exclude = ()
        return super().get_form(request, obj, **kwargs)


@admin.register(SolicitudVacaciones)
class SolicitudVacacionesAdmin(admin.ModelAdmin):
    list_display = ('colaborador', 'fecha_inicio', 'fecha_fin', 'estado', 'dias_solicitados')
    list_filter = ('estado', 'fecha_solicitud')
    search_fields = ('colaborador__dni', 'colaborador__user__first_name')

    # 1. Filtro para que cada quien vea solo sus vacaciones
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.groups.filter(name__in=['Administración y RRHH', 'Supervisores de Operaciones']).exists():
            return qs
        return qs.filter(colaborador__user=request.user)

    # 2. Asignación automática del solicitante
    def save_model(self, request, obj, form, change):
        if not change:
            if not hasattr(obj, 'colaborador') or not obj.colaborador:
                if hasattr(request.user, 'colaborador'):
                    obj.colaborador = request.user.colaborador
        super().save_model(request, obj, form, change)

    # 3. Ocultar el campo 'colaborador' a los usuarios base
    def get_form(self, request, obj=None, **kwargs):
        if not request.user.is_superuser and not request.user.groups.filter(name__in=['Administración y RRHH', 'Supervisores de Operaciones']).exists():
            self.exclude = ('colaborador',)
        else:
            self.exclude = ()
        return super().get_form(request, obj, **kwargs)