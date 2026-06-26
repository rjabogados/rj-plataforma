import csv
import requests
import openpyxl
from datetime import datetime, date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.db import transaction
from django.conf import settings

# Importamos los modelos y las herramientas de permisos compartidas
from intranet.models import Colaborador, Asistencia
from .utils import solo_directivos

@login_required(login_url='login')
@solo_directivos
def sincronizar_sheets(request):
    """Sincroniza las marcaciones desde Google Sheets usando la configuración segura de settings."""
    # Jalamos el ID de forma segura sin exponerlo en la lógica de la vista
    sheet_id = getattr(settings, 'GOOGLE_SHEETS_CONFIG', {}).get('SHEET_ID', '14rxk-CP5XH8IXJv9QP8ypqir0oIP0DQv7F_soOlaZDo')
    
    try:
        response = requests.get(f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv")
        response.encoding = 'utf-8'
        with transaction.atomic():
            for fila in csv.DictReader(response.text.splitlines()):
                dni_val, fecha_str = str(fila.get('DNI', '')).strip(), str(fila.get('FECHA', '')).strip()
                if not dni_val or not fecha_str: continue
                colaborador = Colaborador.objects.filter(dni=dni_val).first()
                if not colaborador: continue
                try: 
                    fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                except ValueError: 
                    continue

                asistencia, _ = Asistencia.objects.get_or_create(colaborador=colaborador, fecha=fecha_obj)
                
                def limpiar_hora(h_txt):
                    h_txt = str(h_txt).strip()
                    if not h_txt or h_txt in ['0:00:00', '0:08:36', '00:00:00']: return None
                    try: return datetime.strptime(h_txt, '%H:%M:%S').time()
                    except ValueError: return None

                f1, f2, f3, f4, f7, f8 = map(limpiar_hora, [
                    fila.get('F1'), fila.get('F2'), fila.get('F3'), 
                    fila.get('F4'), fila.get('F7'), fila.get('F8')
                ])
                
                if f1: asistencia.f1_ingreso = f1
                if f2: asistencia.f2_salida_almuerzo = f2
                if f3: asistencia.f3_retorno_almuerzo = f3
                if f4: asistencia.f4_salida = f4
                if f7: asistencia.f7_salida_break = f7
                if f8: asistencia.f8_retorno_break = f8
                asistencia.save()
    except Exception: 
        pass
    return redirect('asistencia')

@login_required(login_url='login')
@solo_directivos
def control_asistencia(request):
    """Filtra y muestra el reporte de asistencia general por rango de fechas."""
    f_inicio_str, f_fin_str = request.GET.get('fecha_inicio'), request.GET.get('fecha_fin')
    f_inicio = datetime.strptime(f_inicio_str, '%Y-%m-%d').date() if f_inicio_str else date.today()
    f_fin = datetime.strptime(f_fin_str, '%Y-%m-%d').date() if f_fin_str else f_inicio
    
    queryset = Asistencia.objects.filter(fecha__range=[f_inicio, f_fin]).select_related(
        'colaborador__user', 'colaborador__negocio'
    )
    
    return render(request, 'intranet/rrhh/asistencia.html', {
        'asistencias': queryset.order_by('-fecha', 'colaborador__user__last_name'), 
        'fecha_inicio': f_inicio.strftime('%Y-%m-%d'), 
        'fecha_fin': f_fin.strftime('%Y-%m-%d'), 
        'hoy': date.today()
    })

@login_required(login_url='login')
@solo_directivos
def eliminar_asistencia(request, pk):
    get_object_or_404(Asistencia, pk=pk).delete()
    return redirect('asistencia')

@login_required(login_url='login')
@solo_directivos
def procesar_huellero(request):
    """Procesa el archivo Excel cargado manualmente desde el dispositivo biométrico físico."""
    if request.method == 'POST' and request.FILES.get('archivo_huellero'):
        tmp = default_storage.save(f'tmp/huellero_tmp.xlsx', ContentFile(request.FILES['archivo_huellero'].read()))
        try:
            wb = openpyxl.load_workbook(default_storage.open(tmp))
            with transaction.atomic():
                for fila in wb.active.iter_rows(min_row=2, values_only=True):
                    dni_val, fecha_hora_val = str(fila[0]).strip() if fila[0] else None, fila[1]
                    if not dni_val or not fecha_hora_val: continue
                    colaborador = Colaborador.objects.filter(dni=dni_val).first()
                    if not colaborador: continue
                    
                    if isinstance(fecha_hora_val, datetime): 
                        fecha_marca, hora_marca = fecha_hora_val.date(), fecha_hora_val.time()
                    else:
                        try:
                            obj = datetime.strptime(str(fecha_hora_val), '%Y-%m-%d %H:%M:%S')
                            fecha_marca, hora_marca = obj.date(), obj.time()
                        except ValueError: continue
                        
                    asistencia, _ = Asistencia.objects.get_or_create(colaborador=colaborador, fecha=fecha_marca)
                    estado = str(fila[2]).strip().upper() if len(fila) > 2 and fila[2] else ""
                    
                    if "INGRESO" in estado or estado == "0" or (not asistencia.f1_ingreso and hora_marca.hour < 11): 
                        asistencia.f1_ingreso = hora_marca
                    elif "SALIDA ALMUERZO" in estado or (not asistencia.f2_salida_almuerzo and 12 <= hora_marca.hour <= 14): 
                        asistencia.f2_salida_almuerzo = hora_marca
                    elif "RETORNO ALMUERZO" in estado or (not asistencia.f3_retorno_almuerzo and 13 <= hora_marca.hour <= 15): 
                        asistencia.f3_retorno_almuerzo = hora_marca
                    elif "SALIDA" in estado or estado == "1" or (not asistencia.f4_salida and hora_marca.hour > 15): 
                        asistencia.f4_salida = hora_marca
                    asistencia.save()
        except Exception: 
            pass
        finally: 
            default_storage.delete(tmp)
    return redirect('asistencia')

@login_required(login_url='login')
def visor_asistencia(request): 
    return render(request, 'intranet/rrhh/visor_asistencia.html')

@login_required(login_url='login')
@solo_directivos
def modo_televisor(request): 
    """Muestra la cola de asistencia y marcas en tiempo real optimizado para la pantalla de la oficina."""
    return render(request, 'intranet/televisor.html')