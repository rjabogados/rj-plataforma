from django.contrib import admin
from intranet.models.lms import (
    CursoInduccion, MaterialFormativo, EvaluacionCurso, 
    PreguntaEvaluacion, OpcionRespuesta, MatriculaCurso, RespuestaColaborador
)

# =========================================================
# 1. CURSOS Y MATERIALES (CON SMART TARGETING)
# =========================================================
class CursoInduccionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'tipo', 'publico_general', 'rol_permitido', 'cartera_vinculada', 'activo')
    list_filter = ('tipo', 'publico_general', 'rol_permitido', 'activo')
    search_fields = ('titulo', 'descripcion')

class MaterialFormativoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'curso', 'tipo', 'orden')
    list_filter = ('tipo', 'curso')

# =========================================================
# 2. MOTOR DE EXÁMENES (LO QUE YA TENÍAS)
# =========================================================
class OpcionRespuestaInline(admin.TabularInline):
    model = OpcionRespuesta
    extra = 4

class PreguntaEvaluacionAdmin(admin.ModelAdmin):
    inlines = [OpcionRespuestaInline]
    list_display = ['enunciado', 'evaluacion', 'puntos', 'activa']
    list_filter = ['evaluacion', 'activa']
    search_fields = ['enunciado']

class EvaluacionCursoAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'curso', 'tiempo_limite_minutos', 'puntaje_aprobatorio', 'activa']
    list_filter = ['activa']

class MatriculaCursoAdmin(admin.ModelAdmin):
    list_display = ['colaborador', 'curso', 'estado', 'nota_obtenida']
    list_filter = ['estado', 'curso']

# =========================================================
# 3. REGISTRAMOS TODO EN EL PANEL
# =========================================================
admin.site.register(CursoInduccion, CursoInduccionAdmin)
admin.site.register(MaterialFormativo, MaterialFormativoAdmin)
admin.site.register(EvaluacionCurso, EvaluacionCursoAdmin)
admin.site.register(PreguntaEvaluacion, PreguntaEvaluacionAdmin)
admin.site.register(MatriculaCurso, MatriculaCursoAdmin)
admin.site.register(RespuestaColaborador)