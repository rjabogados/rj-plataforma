# Generated manually
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('intranet', '0034_alter_solicitudvacaciones_estado_alter_ticket_estado'),
    ]

    operations = [
        migrations.AddField(
            model_name='colaborador',
            name='permitir_mensajes_cumpleanos',
            field=models.BooleanField(default=True, verbose_name='Permitir Mensajes de Cumpleaños'),
        ),
    ]
