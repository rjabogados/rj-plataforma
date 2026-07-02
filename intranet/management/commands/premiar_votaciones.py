from django.core.management.base import BaseCommand
from datetime import date
from django.db.models import Count
from intranet.models.comunicacion import CategoriaVotacion, VotoMensual, Reconocimiento
from intranet.models.rrhh_core import Colaborador

class Command(BaseCommand):
    help = 'Calcula los ganadores de votaciones del mes anterior y les otorga puntos.'

    def handle(self, *args, **kwargs):
        hoy = date.today()
        # Evaluamos el mes anterior
        mes_anterior = hoy.month - 1 if hoy.month > 1 else 12
        anio_anterior = hoy.year if hoy.month > 1 else hoy.year - 1

        categorias = CategoriaVotacion.objects.filter(activa=True)
        colaboradores = Colaborador.objects.filter(user__is_active=True)

        for cat in categorias:
            # Agrupar por cartera (negocio o subcartera no está estrictamente en un campo fácil de group_by)
            # Para simplificar y hacerlo exacto, iteraremos por los ganadores que la vista calcula
            # En la vida real, lo mejor es hacer un annotate general:
            votos = VotoMensual.objects.filter(categoria=cat, mes=mes_anterior, anio=anio_anterior)
            if not votos.exists():
                continue
                
            # Calculamos ganadores globales por simplicidad en el cron, o si es por cartera, debemos iterar
            # Para este comando, otorgaremos puntos a todos los que hayan recibido más de 0 votos? No, solo a los ganadores.
            ganador_id = votos.values('candidato').annotate(total=Count('candidato')).order_by('-total').first()
            
            if ganador_id:
                colab = Colaborador.objects.get(id=ganador_id['candidato'])
                # Verificar si ya se le otorgó premio este mes por esta categoría
                msg = f"Ganador(a) en {cat.nombre} ({mes_anterior}/{anio_anterior})"
                if not Reconocimiento.objects.filter(receptor=colab, mensaje=msg).exists():
                    Reconocimiento.objects.create(
                        emisor=Colaborador.objects.filter(rol='RRHH').first() or colab, # fallback
                        receptor=colab,
                        tipo='ESTRELLA',
                        mensaje=msg,
                        puntos_otorgados=50
                    )
                    colab.puntos_acumulados += 50
                    colab.puntos_disponibles += 50
                    colab.save()
                    self.stdout.write(self.style.SUCCESS(f'Puntos otorgados a {colab.user.first_name} por {cat.nombre}'))
