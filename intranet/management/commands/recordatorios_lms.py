from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from intranet.models import Notificacion
from intranet.models.lms import MatriculaCurso


class Command(BaseCommand):
    help = 'Genera recordatorios automáticos LMS para módulos próximos a vencer o vencidos.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias-anticipacion',
            type=int,
            default=2,
            help='Dias antes de la fecha limite para recordar (default: 2).',
        )
        parser.add_argument(
            '--solo-vencidos',
            action='store_true',
            help='Si se usa, solo notifica modulos vencidos.',
        )

    def handle(self, *args, **options):
        hoy = timezone.localdate()
        dias_anticipacion = max(options['dias_anticipacion'], 0)
        solo_vencidos = options['solo_vencidos']

        pendientes = MatriculaCurso.objects.filter(
            estado__in=['PENDIENTE', 'EN_CURSO', 'REPROBADO'],
            fecha_limite__isnull=False,
        ).select_related('colaborador__user', 'curso')

        creadas = 0
        for matricula in pendientes:
            fecha_limite = matricula.fecha_limite
            if fecha_limite < hoy:
                titulo = 'Recordatorio: modulo vencido'
                detalle = f"El modulo '{matricula.curso.titulo}' vencio el {fecha_limite.strftime('%d/%m/%Y')}."
            else:
                if solo_vencidos:
                    continue
                if fecha_limite > hoy + timedelta(days=dias_anticipacion):
                    continue
                titulo = 'Recordatorio: modulo por vencer'
                detalle = f"El modulo '{matricula.curso.titulo}' vence el {fecha_limite.strftime('%d/%m/%Y')}."

            # Evita notificaciones duplicadas para el mismo dia.
            ya_existe = Notificacion.objects.filter(
                usuario=matricula.colaborador.user,
                tipo='ALERTA',
                titulo=titulo,
                detalle=detalle,
                url_destino=f"/academia/curso/{matricula.curso_id}/",
                creada_en__date=hoy,
            ).exists()
            if ya_existe:
                continue

            Notificacion.objects.create(
                usuario=matricula.colaborador.user,
                tipo='ALERTA',
                titulo=titulo,
                detalle=detalle,
                url_destino=f"/academia/curso/{matricula.curso_id}/",
            )
            creadas += 1

        self.stdout.write(self.style.SUCCESS(f'Recordatorios generados: {creadas}'))
