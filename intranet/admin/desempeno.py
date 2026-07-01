from django.contrib import admin
from intranet.models import PeriodoEvaluacion, KPI, EvaluacionDesempeno, DetalleEvaluacion

@admin.register(PeriodoEvaluacion)
class PeriodoEvaluacionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'fecha_inicio', 'fecha_fin', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre',)

@admin.register(KPI)
class KPIAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'meta_default')
    search_fields = ('nombre',)

class DetalleEvaluacionInline(admin.TabularInline):
    model = DetalleEvaluacion
    extra = 1

@admin.register(EvaluacionDesempeno)
class EvaluacionDesempenoAdmin(admin.ModelAdmin):
    list_display = ('colaborador', 'evaluador', 'periodo', 'estado', 'nota_final', 'potencial')
    list_filter = ('estado', 'periodo', 'potencial')
    search_fields = ('colaborador__user__first_name', 'colaborador__user__last_name')
    inlines = [DetalleEvaluacionInline]
