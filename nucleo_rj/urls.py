from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from intranet.views.webhook import recibir_matriz_excel

# --- PERSONALIZACIÓN DEL PANEL CORPORATIVO ---
admin.site.site_header = "Intranet RJ Abogados"
admin.site.site_title = "Panel Operativo Central"
admin.site.index_title = "Bienvenido al Sistema Central"
# ---------------------------------------------

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/webhook/', recibir_matriz_excel, name='webhook_matriz'),
]

# SEGURIDAD PARA RENDER: Solo emula el servidor de archivos si estás en tu PC (Desarrollo)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)