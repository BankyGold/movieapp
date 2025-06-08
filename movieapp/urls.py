"""
URL configuration for movieapp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.conf.urls import handler400, handler403, handler404, handler500


# Custom error handlers
handler400 = 'authentication.views.custom_bad_request'  # 400 Bad Request
handler403 = 'authentication.views.custom_permission_denied'  # 403 Forbidden
handler404 = 'authentication.views.custom_page_not_found'  # 404 Not Found
handler500 = 'authentication.views.custom_server_error'  # 500 Internal Server Error


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('authentication.urls')),
    path('football/', include('football.urls')),
    
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
