from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from intranet.views.webhook import recibir_matriz_excel

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('intranet.urls')),
    path('api/webhook/', recibir_matriz_excel, name='webhook_matriz'),
]

# Esto permite abrir los PDFs en el navegador durante el desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)