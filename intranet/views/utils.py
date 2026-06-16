import unicodedata
from functools import wraps
from django.shortcuts import redirect
from django.contrib.auth.models import User

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
            return redirect('inicio')
        return _wrapped_view
    return decorator

solo_directivos = requiere_rol(['ADMINISTRATIVO', 'RRHH', 'GERENCIA'])
solo_calidad = requiere_rol(['CALIDAD', 'SUPERVISOR', 'GERENCIA'])

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

def generar_username_unico(nombres_bruto, apellidos_bruto, dni_val):
    base_username = f"{limpiar_texto_usuario(nombres_bruto)}.{limpiar_texto_usuario(apellidos_bruto)}"
    if not base_username or base_username == ".": base_username = f"usuario.{dni_val}"
    username_final = base_username
    contador = 1
    while User.objects.filter(username=username_final).exists():
        username_final = f"{base_username}{contador}"
        contador += 1
    return username_final