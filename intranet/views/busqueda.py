from django.shortcuts import render
from django.db.models import Q
from django.contrib.auth.decorators import login_required

from intranet.models import Colaborador, CursoInduccion, PlantillaDocumento

@login_required(login_url='login')
def buscador_global(request):
    """
    Motor de búsqueda global que consulta:
    - Perfiles de empleados (Nombre, apellido, cargo)
    - Cursos (Título, descripción)
    - Documentos (Nombre de la plantilla)
    """
    query = request.GET.get('q', '').strip()
    
    colaboradores = []
    cursos = []
    documentos = []
    
    if query:
        # 1. Buscar en Colaboradores
        colaboradores = Colaborador.objects.select_related('user', 'cargo', 'area').filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(cargo__nombre__icontains=query) |
            Q(dni__icontains=query)
        ).distinct()[:10]  # Limitamos a los mejores 10
        
        # 2. Buscar en LMS (Cursos)
        cursos = CursoInduccion.objects.filter(
            Q(titulo__icontains=query) |
            Q(descripcion__icontains=query)
        ).distinct()[:10]
        
        # 3. Buscar en Documentos
        documentos = PlantillaDocumento.objects.filter(
            Q(nombre__icontains=query)
        ).filter(activo=True)[:10]

    return render(request, 'intranet/core/busqueda_resultados.html', {
        'query': query,
        'colaboradores': colaboradores,
        'cursos': cursos,
        'documentos': documentos,
        'page_title': 'Resultados de Búsqueda'
    })
