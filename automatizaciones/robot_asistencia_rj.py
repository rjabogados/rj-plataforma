import os
import time
from datetime import datetime
from zk import ZK
import requests

# =====================================================================
# CONFIGURACIÓN CORPORATIVA - SEDE LOCAL
# =====================================================================
IP_RELOJ = '192.168.22.138'
PORT_RELOJ = 4370
PASSWORD_RELOJ = 1007

# =====================================================================
# TU LINK OFICIAL DE PRODUCCIÓN (CORREGIDO)
# =====================================================================
URL_WEBHOOK_SISTEMAS = "https://script.google.com/macros/s/AKfycbxHj0fWf_jnUH7Wj6PFFbnPg8DUm8UW1G71SD_qbAgIF_lpzdmL2GUfyu8-Sb6Y6gGH/exec"

# Frecuencia de sincronización automática (5 minutos)
TIEMPO_MONITOR = 300 

def iniciar_espejo_nube_total():
    print("=========================================================")
    print("🤖 ROBOT DE RESPALDO Y SINCRONIZACIÓN HISTÓRICA TOTAL v1.0")
    print("⚙️ Red: Conectado localmente al biométrico ZKTeco K14 Pro")
    print(f"⏱️ Modo: Volcado continuo e histórico a la nube cada {int(TIEMPO_MONITOR/60)} minutos.")
    print("=========================================================\n")

    while True:
        print(f"🕒 [{datetime.now().strftime('%H:%M:%S')}] Extrayendo buffer completo de la memoria del reloj...")
        zk = ZK(IP_RELOJ, port=PORT_RELOJ, timeout=15, password=PASSWORD_RELOJ)
        try:
            conn = zk.connect()
            asistencias = conn.get_attendance()
            
            # Matriz organizada por [Fecha][DNI] para agrupar marcas horizontalmente
            control_historico = {}
            
            for registro in asistencias:
                fecha_str = registro.timestamp.strftime('%Y-%m-%d')
                dni = str(int(registro.user_id.strip())) if registro.user_id.strip().isdigit() else str(registro.user_id).strip()
                hora_marca = registro.timestamp.strftime('%H:%M:%S')
                boton = registro.punch
                
                if fecha_str not in control_historico:
                    control_historico[fecha_str] = {}
                    
                if dni not in control_historico[fecha_str]:
                    control_historico[fecha_str][dni] = {
                        "FECHA": fecha_str, 
                        "DNI": dni,
                        "F1": "00:00:00", 
                        "F7": "00:00:00", 
                        "F8": "00:00:00",
                        "F2": "00:00:00", 
                        "F3": "00:00:00", 
                        "F4": "00:00:00"
                    }
                
                # Traducción de botones físicos a las variables de la plataforma
                if boton == 1:   control_historico[fecha_str][dni]["F1"] = hora_marca
                elif boton == 2: control_historico[fecha_str][dni]["F7"] = hora_marca
                elif boton == 3: control_historico[fecha_str][dni]["F8"] = hora_marca
                elif boton == 4: control_historico[fecha_str][dni]["F2"] = hora_marca
                elif boton == 5: control_historico[fecha_str][dni]["F3"] = hora_marca
                elif boton == 6: control_historico[fecha_str][dni]["F4"] = hora_marca

            conn.disconnect()
            
            # Aplanamiento de la matriz para la transmisión JSON
            lista_envio = []
            for f_key in control_historico:
                for d_key in control_historico[f_key]:
                    lista_envio.append(control_historico[f_key][d_key])
            
            print(f"📊 Registros totales consolidados en memoria: {len(lista_envio)} filas.")
            
            if lista_envio:
                headers = {'Content-Type': 'application/json'}
                print("🚀 Transfiriendo base de datos completa a la nube...")
                respuesta = requests.post(URL_WEBHOOK_SISTEMAS, json=lista_envio, headers=headers, timeout=25)
                
                if respuesta.status_code == 200:
                    print("🏆 ¡Éxito total! El repositorio en la nube se encuentra sincronizado y respaldado.")
                else:
                    print(f"⚠️ Alerta: El servidor web respondió con un código de estado: {respuesta.status_code}")
                    
        except Exception as e:
            print(f"❌ Error de comunicación con el hardware o de red: {e}")
            
        print(f"💤 Esperando {int(TIEMPO_MONITOR/60)} minutos para la siguiente actualización...\n")
        time.sleep(TIEMPO_MONITOR)

if __name__ == "__main__":
    try:
        iniciar_espejo_nube_total()
    except KeyboardInterrupt:
        print("\n🛑 Servicio interrumpido manualmente.")