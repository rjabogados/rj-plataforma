import os

with open('mapa_rj.txt', 'w', encoding='utf-8') as archivo:
    for ruta_actual, carpetas, archivos in os.walk('.'):
        # Filtramos las carpetas que no necesitamos que la IA lea
        carpetas[:] = [c for c in carpetas if c not in ['.venv', 'venv', '.git', '__pycache__', 'staticfiles']]
        
        nivel = ruta_actual.count(os.sep)
        sangria = '    ' * nivel
        nombre_carpeta = os.path.basename(ruta_actual) if ruta_actual != '.' else 'Proyecto_Central'
        
        archivo.write(f'{sangria}📁 {nombre_carpeta}/\n')
        
        for arch in archivos:
            if arch != 'mapa.py' and not arch.endswith('.pyc'):
                archivo.write(f'{sangria}    📄 {arch}\n')

print("¡Mapa generado con éxito en mapa_rj.txt!")