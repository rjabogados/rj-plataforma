from intranet.models import Notificacion


def notificaciones_usuario(request):
    if not request.user.is_authenticated:
        return {
            'notificaciones_no_leidas': 0,
            'notificaciones_menu': [],
        }

    notificaciones_qs = Notificacion.objects.filter(usuario=request.user).order_by('-creada_en')
    return {
        'notificaciones_no_leidas': notificaciones_qs.filter(leida=False).count(),
        'notificaciones_menu': list(notificaciones_qs[:7]),
    }
