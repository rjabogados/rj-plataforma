import requests
import json
from datetime import datetime

# La dirección de tu plataforma local
url = "http://localhost:8000/api/recibir-asistencia/"

# Obtenemos la fecha de hoy automáticamente para que coincida con el sistema
hoy_str = datetime.now().strftime('%Y-%m-%d')

# El JSON idéntico al que enviará tu script en producción
payload = [
  {
    "FECHA": hoy_str,
    "DNI": "1007", # <-- CAMBIA ESTO por un DNI que exista en tu plataforma
    "F1": "08:05:30",
    "F7": "13:00:00",
    "F8": "14:00:00",
    "F2": "00:00:00",
    "F3": "00:00:00",
    "F4": "18:05:00"
  }
]

headers = {'Content-Type': 'application/json'}

print("Disparando datos al servidor local...")
try:
    respuesta = requests.post(url, json=payload, headers=headers)
    print(f"Respuesta del servidor: {respuesta.status_code}")
    print(respuesta.json())
except requests.exceptions.ConnectionError:
    print("Error: Asegúrate de que el servidor de Django esté encendido en otra terminal.")