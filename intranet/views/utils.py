import unicodedata
from functools import wraps
from django.shortcuts import redirect
from django.contrib.auth.models import User
from django.contrib import messages

# --- CONTROL DE PERMISOS (RBAC) ---
def requiere_rol(roles_permitidos):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            perfil = getattr(request.user, 'perfil', None)
            if perfil and perfil.rol in roles_permitidos:
                return view_func(request, *args, **kwargs)
            messages.info(request, 'Este modulo no esta habilitado para tu perfil actual. Te mostramos el menu inicial.')
            return redirect('menu_inicial')
        return _wrapped_view
    return decorator

solo_directivos = requiere_rol(['ADMINISTRATIVO', 'RRHH', 'GERENCIA'])
solo_calidad = requiere_rol(['CALIDAD', 'SUPERVISOR', 'GERENCIA'])
solo_supervisores = requiere_rol(['SUPERVISOR', 'GERENCIA', 'ADMINISTRATIVO'])


def _perfil_scope(perfil):
    if not perfil:
        return 'GENERAL'
    if getattr(perfil, 'es_directivo', False):
        return 'ADMINISTRATIVO'
    if getattr(perfil, 'es_operativo', False):
        return 'ASESOR'
    return getattr(perfil, 'scope_plataforma', 'GENERAL')


def filtros_personal_disponibles(perfil):
    scope = _perfil_scope(perfil)
    if scope == 'ASESOR':
        return {'nombre': True, 'documento': True, 'cargo': True, 'area': True, 'cartera': True, 'subcartera': True}
    if scope == 'ADMINISTRATIVO':
        return {'nombre': True, 'documento': True, 'cargo': True, 'area': True, 'cartera': False, 'subcartera': False}
    return {'nombre': True, 'documento': True, 'cargo': False, 'area': False, 'cartera': False, 'subcartera': False}


def filtrar_colaboradores(queryset, params, perfil=None):
    from django.db.models import Q

    busqueda = (params.get('q') or '').strip()
    documento = (params.get('documento') or '').strip()
    cargo = (params.get('cargo') or '').strip()
    area = (params.get('area') or '').strip()
    cartera = (params.get('cartera') or '').strip()
    subcartera = (params.get('subcartera') or '').strip()

    visibilidad = filtros_personal_disponibles(perfil)

    sede = (params.get('sede') or '').strip()

    if busqueda:
        queryset = queryset.filter(
            Q(user__first_name__icontains=busqueda) |
            Q(user__last_name__icontains=busqueda) |
            Q(user__username__icontains=busqueda) |
            Q(dni__icontains=busqueda)
        )

    if documento:
        queryset = queryset.filter(dni__icontains=documento)

    if visibilidad.get('cargo') and cargo:
        queryset = queryset.filter(cargo_id=cargo)

    if visibilidad.get('area') and area:
        queryset = queryset.filter(area_id=area)

    if visibilidad.get('cartera') and cartera:
        queryset = queryset.filter(negocio_id=cartera)

    if visibilidad.get('subcartera') and subcartera:
        queryset = queryset.filter(subcartera__icontains=subcartera)

    # El filtro de sede está disponible para todos los que puedan filtrar
    if sede:
        queryset = queryset.filter(sede=sede)

    return queryset


def perfil_coincide_segmentacion(perfil, *, rol=None, area=None, cargo=None, cartera=None, subcartera=None, publico_general=False):
    if publico_general:
        return True
    if not perfil:
        return False

    if rol and perfil.rol == rol:
        return True
    if area and getattr(perfil, 'area_id', None) == getattr(area, 'id', area):
        return True
    if cargo and getattr(perfil, 'cargo_id', None) == getattr(cargo, 'id', cargo):
        return True
    if cartera and getattr(perfil, 'negocio_id', None) == getattr(cartera, 'id', cartera):
        return True
    if subcartera and (perfil.subcartera or '') and str(perfil.subcartera).strip().lower() == str(subcartera).strip().lower():
        return True

    return False

# --- HERRAMIENTAS GLOBALES ---
def obtener_ip_cliente(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')

def limpiar_texto_usuario(texto):
    if not texto: return ""
    texto = str(texto).strip().lower()
    palabras = texto.split()
    primera_palabra = palabras[0] if palabras else ""
    return ''.join(c for c in unicodedata.normalize('NFKD', primera_palabra) if unicodedata.category(c) != 'Mn').replace('ñ', 'n')

def generar_username_unico(nombres_bruto, apellidos_bruto, dni_val=None):
    base_username = f"{limpiar_texto_usuario(nombres_bruto)}.{limpiar_texto_usuario(apellidos_bruto)}"
    if not base_username or base_username == ".":
        base_username = f"usuario.{str(dni_val).strip()}" if dni_val else "usuario"
    username_final = base_username
    contador = 1
    while User.objects.filter(username=username_final).exists():
        username_final = f"{base_username}{contador}"
        contador += 1
    return username_final