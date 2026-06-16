from django.contrib import admin
from intranet.models import (
    CursoInduccion, MaterialFormativo, EvaluacionCurso, PreguntaEvaluacion, 
    MatriculaCurso, RespuestaColaborador, Encuesta, Pregunta, 
    RespuestaEncuesta, CandidatoOnboarding
)

@admin.register(CursoInduccion)
class CursoInduccionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'tipo', 'activo', 'fecha_creacion')
    list_filter = ('tipo', 'activo')
    search_fields = ('titulo',)

@admin.register(MaterialFormativo)
class MaterialFormativoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'curso', 'tipo', 'orden')
    list_filter = ('tipo', 'curso')

@admin.register(MatriculaCurso)
class MatriculaCursoAdmin(admin.ModelAdmin):
    list_display = ('colaborador', 'curso', 'estado', 'nota_obtenida')
    list_filter = ('estado', 'curso')
    search_fields = ('colaborador__user__first_name', 'colaborador__user__last_name')

@admin.register(Encuesta)
class EncuestaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'es_anonima', 'activa', 'fecha_creacion')
    list_filter = ('activa', 'es_anonima')

@admin.register(CandidatoOnboarding)
class CandidatoOnboardingAdmin(admin.ModelAdmin):
    list_display = ('nombres', 'apellidos', 'dni', 'puesto_esperado', 'estado')
    list_filter = ('estado', 'puesto_esperado', 'campaña_destino')
    search_fields = ('dni', 'nombres', 'apellidos')

# Registramos los modelos secundarios de forma rápida y sencilla
admin.site.register(EvaluacionCurso)
admin.site.register(PreguntaEvaluacion)
admin.site.register(RespuestaColaborador)
admin.site.register(Pregunta)
admin.site.register(RespuestaEncuesta)