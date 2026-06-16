from django.core.management.base import BaseCommand
from django.utils import timezone
from intranet.models import Colaborador, Asistencia
from zk import ZK
import time

class Command(BaseCommand):
    help = 'Demonio de sincronización TCP/IP con reloj ZKTeco K14 Pro cada 5 minutos'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('==== ROBOT ZKTECO INICIADO ===='))
        self.stdout.write('Presiona Ctrl + C para detener la sincronización.\n')
        
        # Parámetros de Hardware
        IP_RELOJ = '192.168.22.138'
        PUERTO = 4370
        CLAVE = 1007
        INTERVALO_SEGUNDOS = 300  # 5 minutos

        while True:
            # Inicializamos el objeto cliente
            zk = ZK(IP_RELOJ, port=PUERTO, timeout=10, password=CLAVE, force_udp=False, ommit_ping=False)
            conn = None
            
            try:
                hora_actual = timezone.now().strftime("%H:%M:%S")
                self.stdout.write(f'[{hora_actual}] Abriendo socket hacia {IP_RELOJ}...')
                
                # 1. Conexión al equipo
                conn = zk.connect()
                
                # 2. Extracción del buffer completo
                attendances = conn.get_attendance()
                hoy = timezone.now().date()
                
                # 3. Filtro en memoria (Solo marcaciones de hoy)
                marcaciones_hoy = [att for att in attendances if att.timestamp.date() == hoy]
                
                if marcaciones_hoy:
                    self.stdout.write(self.style.SUCCESS(f'[{hora_actual}] Se encontraron {len(marcaciones_hoy)} marcaciones para hoy. Procesando...'))
                    
                    for att in marcaciones_hoy:
                        dni_val = str(att.user_id).strip()
                        hora_marca = att.timestamp.time()
                        
                        # Buscar si el trabajador existe en la BD
                        colaborador = Colaborador.objects.filter(dni=dni_val).first()
                        if not colaborador:
                            continue  # Si marca alguien que no está en la Intranet, lo ignoramos
                            
                        # Buscar o crear su asistencia de hoy
                        asistencia, _ = Asistencia.objects.get_or_create(
                            colaborador=colaborador, 
                            fecha=hoy
                        )
                        
                        # Lógica de asignación (F1 a F4) basada en el horario
                        if not asistencia.f1_ingreso and hora_marca.hour < 11:
                            asistencia.f1_ingreso = hora_marca
                        elif not asistencia.f2_salida_almuerzo and 12 <= hora_marca.hour <= 14:
                            asistencia.f2_salida_almuerzo = hora_marca
                        elif not asistencia.f3_retorno_almuerzo and 13 <= hora_marca.hour <= 15:
                            asistencia.f3_retorno_almuerzo = hora_marca
                        elif not asistencia.f4_salida and hora_marca.hour > 15:
                            asistencia.f4_salida = hora_marca
                            
                        asistencia.save()
                else:
                    self.stdout.write(f'[{hora_actual}] Buffer leído. Sin marcaciones nuevas para hoy.')
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'[{timezone.now().strftime("%H:%M:%S")}] ERROR de comunicación: {e}'))
                
            finally:
                # 4. CIERRE INMEDIATO DEL SOCKET (Crítico para evitar bloqueo del puerto)
                if conn:
                    conn.disconnect()
                    self.stdout.write(f'Socket desconectado limpiamente.')
            
            # 5. Pausa de 5 minutos antes del siguiente ciclo
            self.stdout.write(f'Esperando {INTERVALO_SEGUNDOS/60} minutos...\n')
            time.sleep(INTERVALO_SEGUNDOS)