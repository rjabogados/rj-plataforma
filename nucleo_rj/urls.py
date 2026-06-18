from django.contrib import admin
from django.urls import path, include  # <- Importamos 'include' para conectar tu intranet
from django.conf import settings
from django.conf.urls.static import static
from intranet.views.webhook import recibir_matriz_excel

# --- PERSONALIZACIÓN DEL PANEL CORPORATIVO (BACKOFFICE) ---
admin.site.site_header = "Intranet RJ Abogados"
admin.site.site_title = "Panel Operativo Central"
admin.site.index_title = "Bienvenido al Sistema Central"
# ---------------------------------------------

urlpatterns = [
    # 1. LA PUERTA PRINCIPAL: Conecta directamente con tu plataforma normal e intranet
    path('', include('intranet.urls')), 
    
    # 2. El panel de administración por detrás
    path('admin/', admin.site.urls),
    
    # 3. El webhook de Meta Ads
    path('api/webhook/', recibir_matriz_excel, name='webhook_matriz'),
]

# SEGURIDAD PARA RENDER: Solo emula el servidor de archivos si estás en tu PC (Desarrollo)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)