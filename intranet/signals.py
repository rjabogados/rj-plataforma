from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User, Group

from intranet.models import MensajeInterno, Notificacion, Ticket, SolicitudVacaciones

@receiver(post_save, sender=User)
def asignar_grupo_por_defecto(sender, instance, created, **kwargs):
    if created:  
        grupo_base, _ = Group.objects.get_or_create(name='Personal Base')
        instance.groups.add(grupo_base)
        instance.is_staff = True
        instance.save()


@receiver(post_save, sender=MensajeInterno)
def notificar_mensaje_interno(sender, instance, created, **kwargs):
    if not created:
        return
    Notificacion.objects.create(
        usuario=instance.destinatario.user,
        tipo='MENSAJE',
        titulo=f'Nuevo mensaje: {instance.asunto}',
        detalle=f'De: {instance.remitente.user.get_full_name() or instance.remitente.user.username}',
        url_destino=f'/mensajeria/leer/{instance.id}/',
    )


def _usuarios_rrhh_y_directivos():
    return User.objects.filter(
        perfil__rol__in=['RRHH', 'ADMINISTRATIVO', 'GERENCIA']
    ).distinct()


@receiver(post_save, sender=Ticket)
def notificar_ticket_pendiente(sender, instance, created, **kwargs):
    if not created or instance.estado != 'PENDIENTE':
        return

    nombre_colaborador = instance.colaborador.user.get_full_name() or instance.colaborador.user.username
    for usuario in _usuarios_rrhh_y_directivos():
        Notificacion.objects.create(
            usuario=usuario,
            tipo='TICKET',
            titulo='Nuevo ticket pendiente',
            detalle=f'{nombre_colaborador} registró un ticket ({instance.get_tipo_display()})',
            url_destino='/tickets-admin/',
        )


@receiver(post_save, sender=SolicitudVacaciones)
def notificar_solicitud_vacaciones(sender, instance, created, **kwargs):
    if not created or instance.estado != 'PENDIENTE':
        return

    nombre_colaborador = instance.colaborador.user.get_full_name() or instance.colaborador.user.username
    for usuario in _usuarios_rrhh_y_directivos():
        Notificacion.objects.create(
            usuario=usuario,
            tipo='VACACIONES',
            titulo='Nueva solicitud de vacaciones',
            detalle=f'{nombre_colaborador} solicitó {instance.dias_solicitados} día(s)',
            url_destino='/vacaciones-admin/',
        )