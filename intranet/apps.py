import os
import threading
from django.apps import AppConfig

class IntranetConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'intranet'

    def ready(self):
        # 1. Activamos las señales para la asignación automática de Personal Base
        # Al estar aquí arriba, funcionará perfecto tanto en tu computadora como en Render
        import intranet.signals

        # El Candado: Evita que el "StatReloader" de Django clone el proceso al guardar archivos en desarrollo local
        if os.environ.get('RUN_MAIN') == 'true':
            
            try:
                # Importamos el robot aquí adentro para evitar errores de carga circular
                from automatizaciones.robot_asistencia_rj import iniciar_espejo_nube_total
                
                print("\n🤖 [SISTEMA] Iniciando módulo de sincronización biométrica en segundo plano...")
                
                # Lanzamos el robot en un "Hilo" (Thread) para no bloquear la intranet
                # daemon=True asegura que el robot se apague cuando tú apagues el servidor
                hilo_robot = threading.Thread(target=iniciar_espejo_nube_total, daemon=True)
                hilo_robot.start()
                
            except ImportError as e:
                print(f"⚠️ [SISTEMA] No se pudo cargar el robot biométrico: {e}")