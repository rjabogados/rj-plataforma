import re

from django.core.management.base import BaseCommand
from django.db import transaction

from intranet.models import CandidatoReclutamiento


def limpiar_texto(valor):
    return ' '.join(str(valor or '').strip().split())


def limpiar_documento(valor):
    return ''.join(ch for ch in str(valor or '') if ch.isalnum())[:20]


def limpiar_telefono(valor):
    return ''.join(ch for ch in str(valor or '') if ch.isdigit() or ch == '+')[:20]


def normalizar_estado(valor):
    texto = limpiar_texto(valor).lower()
    mapa = {
        'nuevo': 'Nuevo',
        'pendiente': 'Pendiente',
        'entrevista': 'Entrevista agendada',
        'entrevista agendada': 'Entrevista agendada',
        'apto': 'Apto',
        'no apto': 'No apto',
        'no interesado': 'No interesados',
        'no interesados': 'No interesados',
        'contratado': 'Contratado',
    }
    return mapa.get(texto, limpiar_texto(valor)[:50] or 'Nuevo')


def limpiar_estructura(valor):
    texto = limpiar_texto(valor)
    if not texto:
        return []
    return [parte.strip() for parte in re.split(r'[\|/;,:>-]+', texto) if parte and parte.strip()]


class Command(BaseCommand):
    help = 'Limpia, normaliza y consolida la matriz de reclutamiento.'

    def add_arguments(self, parser):
        parser.add_argument('--solo-reporte', action='store_true', help='Muestra los cambios sin guardarlos.')

    def handle(self, *args, **options):
        solo_reporte = options['solo_reporte']
        candidatos = CandidatoReclutamiento.objects.all().order_by('documento', '-fecha_registro')

        actualizados = 0
        eliminados = 0
        duplicados_consolidados = 0
        sin_documento = 0

        vistos = {}

        with transaction.atomic():
            for candidato in candidatos:
                candidato.nombre = limpiar_texto(candidato.nombre)
                candidato.documento = limpiar_documento(candidato.documento)
                candidato.telefono = limpiar_telefono(candidato.telefono)
                candidato.estado_candidato = normalizar_estado(candidato.estado_candidato)
                candidato.sede = limpiar_texto(candidato.sede) or 'No Asignado'
                candidato.canal = limpiar_texto(candidato.canal) or 'Por Definir'

                if not candidato.documento:
                    sin_documento += 1
                    if not solo_reporte:
                        candidato.save()
                    continue

                if candidato.documento in vistos:
                    base = vistos[candidato.documento]
                    base.nombre = base.nombre if len(base.nombre or '') >= len(candidato.nombre or '') else candidato.nombre
                    base.telefono = base.telefono if len(base.telefono or '') >= len(candidato.telefono or '') else candidato.telefono
                    base.estado_candidato = candidato.estado_candidato or base.estado_candidato
                    base.sede = candidato.sede or base.sede
                    base.canal = candidato.canal or base.canal
                    if not solo_reporte:
                        base.save()
                        candidato.delete()
                    duplicados_consolidados += 1
                    eliminados += 1
                    continue

                vistos[candidato.documento] = candidato
                actualizados += 1
                if not solo_reporte:
                    candidato.save()

        if solo_reporte:
            transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS('Matriz de reclutamiento procesada.'))
        self.stdout.write(f'Actualizados: {actualizados}')
        self.stdout.write(f'Duplicados consolidados: {duplicados_consolidados}')
        self.stdout.write(f'Eliminados: {eliminados}')
        self.stdout.write(f'Sin documento: {sin_documento}')