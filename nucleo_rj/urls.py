from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from intranet.views.webhook import recibir_matriz_excel

# --- PERSONALIZACIÓN DEL PANEL CORPORATIVO ---
admin.site.site_header = "Intranet RJ Abogados"
admin.site.site_title = "Panel Operativo Central"
admin.site.index_title = "Bienvenido al Sistema Central"
# ---------------------------------------------

urlpatterns = [
    # 1. Tu plataforma principal
    path('', include('intranet.urls')), 
    
    path('admin/', admin.site.urls),
    path('api/webhook/', recibir_matriz_excel, name='webhook_matriz'),
]

from django.urls import re_path
from django.views.static import serve

# SEGURIDAD Y DESPLIEGUE: Forzar carga de media y estáticos en Railway (DEBUG=False)
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {
        'document_root': settings.MEDIA_ROOT,
    }),
    re_path(r'^static/(?P<path>.*)$', serve, {
        'document_root': settings.STATIC_ROOT,
    }),
]