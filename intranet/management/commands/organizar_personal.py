from django.core.management.base import BaseCommand
from django.db import transaction

from intranet.models import Area, Cargo, Colaborador


ROLE_AREA_MAP = {
    'ASESOR': 'Operaciones',
    'BACKOFFICE': 'Operaciones',
    'CALIDAD': 'Calidad',
    'SUPERVISOR': 'Calidad',
    'SISTEMAS': 'Sistemas',
    'ADMINISTRATIVO': 'Administracion',
    'RRHH': 'Recursos Humanos',
    'GERENCIA': 'Gerencia',
}


class Command(BaseCommand):
    help = 'Ordena y completa catalogos de personal (areas, cargos y subcarteras) segun lo existente en la plataforma.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--solo-reporte',
            action='store_true',
            help='Muestra el analisis sin realizar cambios en la base de datos.',
        )

    def handle(self, *args, **options):
        solo_reporte = options['solo_reporte']

        colaboradores = Colaborador.objects.select_related('area', 'cargo').all()
        total = colaboradores.count()

        cambios_subcartera = 0
        cambios_area_por_cargo = 0
        asignaciones_cargo = 0
        areas_creadas = 0
        cargos_creados = 0

        subcarteras_unicas = set()
        areas_cache = {a.nombre.casefold(): a for a in Area.objects.all()}
        cargos_cache = {(c.area_id, c.nombre.casefold()): c for c in Cargo.objects.select_related('area').all()}
        areas_planeadas = set()
        cargos_planeados = set()

        with transaction.atomic():
            for colab in colaboradores:
                subcartera_raw = colab.subcartera or ''
                subcartera_limpia = ' '.join(subcartera_raw.split()).strip()
                if subcartera_limpia:
                    subcarteras_unicas.add(subcartera_limpia.casefold())
                if subcartera_raw != subcartera_limpia:
                    cambios_subcartera += 1
                    if not solo_reporte:
                        colab.subcartera = subcartera_limpia or None
                        colab.save(update_fields=['subcartera'])

                if colab.cargo and colab.cargo.area and not colab.area:
                    cambios_area_por_cargo += 1
                    if not solo_reporte:
                        colab.area = colab.cargo.area
                        colab.save(update_fields=['area'])

                if not colab.cargo:
                    area_nombre = ROLE_AREA_MAP.get(colab.rol, 'General')
                    area_key = area_nombre.casefold()
                    area_obj = areas_cache.get(area_key)
                    if not area_obj:
                        if solo_reporte:
                            if area_key not in areas_planeadas:
                                areas_planeadas.add(area_key)
                                areas_creadas += 1
                            area_obj = None
                        else:
                            area_obj = Area.objects.create(nombre=area_nombre, activa=True)
                            areas_cache[area_key] = area_obj
                            areas_creadas += 1

                    cargo_nombre = colab.get_rol_display()
                    cargo_key = (area_obj.id if area_obj else area_key, cargo_nombre.casefold())
                    cargo_obj = cargos_cache.get(cargo_key)
                    if not cargo_obj:
                        if solo_reporte:
                            if cargo_key not in cargos_planeados:
                                cargos_planeados.add(cargo_key)
                                cargos_creados += 1
                        elif area_obj:
                            cargo_obj = Cargo.objects.create(area=area_obj, nombre=cargo_nombre, activa=True)
                            cargos_cache[(area_obj.id, cargo_nombre.casefold())] = cargo_obj
                            cargos_creados += 1

                    asignaciones_cargo += 1
                    if not solo_reporte and cargo_obj:
                        colab.cargo = cargo_obj
                        if not colab.area:
                            colab.area = area_obj
                        colab.save(update_fields=['cargo', 'area'])

            if solo_reporte:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS('Analisis de organizacion de personal completado.'))
        self.stdout.write(f'Colaboradores analizados: {total}')
        self.stdout.write(f'Subcarteras normalizadas: {cambios_subcartera}')
        self.stdout.write(f'Areas alineadas desde cargo: {cambios_area_por_cargo}')
        self.stdout.write(f'Cargos asignados por rol: {asignaciones_cargo}')
        self.stdout.write(f'Areas nuevas: {areas_creadas}')
        self.stdout.write(f'Cargos nuevos: {cargos_creados}')
        self.stdout.write(f'Subcarteras unicas detectadas: {len(subcarteras_unicas)}')
