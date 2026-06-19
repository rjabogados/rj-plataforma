from django.contrib import admin
from intranet.models.lms import EvaluacionCurso, PreguntaEvaluacion, OpcionRespuesta, MatriculaCurso, RespuestaColaborador

class OpcionRespuestaInline(admin.TabularInline):
    model = OpcionRespuesta
    extra = 4

class PreguntaEvaluacionAdmin(admin.ModelAdmin):
    inlines = [OpcionRespuestaInline]
    list_display = ['enunciado', 'evaluacion', 'puntos', 'activa']
    list_filter = ['evaluacion', 'activa']
    search_fields = ['enunciado']

class EvaluacionCursoAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'curso', 'duracion_minutos', 'puntaje_aprobatorio', 'activa']
    list_filter = ['activa']

class MatriculaCursoAdmin(admin.ModelAdmin):
    list_display = ['colaborador', 'curso', 'estado', 'nota_obtenida']
    list_filter = ['estado', 'curso']

# Registramos todo
admin.site.register(EvaluacionCurso, EvaluacionCursoAdmin)
admin.site.register(PreguntaEvaluacion, PreguntaEvaluacionAdmin)
admin.site.register(MatriculaCurso, MatriculaCursoAdmin)
admin.site.register(RespuestaColaborador)