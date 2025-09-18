"""
URL configuration for pw_analyst project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from django.urls import include, path

from core.views import CustomLoginView, CustomLogoutView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", CustomLoginView.as_view(), name="login"),
    path("accounts/logout/", CustomLogoutView.as_view(), name="logout"),
    path("accounts/", include("django.contrib.auth.urls")),
    # Applications principales
    path("", include("core.urls")),
    path("projects/", include("projects.urls")),
    path("", include("testing.urls")),
    path("integrations/", include("integrations.urls")),
    path("api/", include("api.urls")),
]

# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Gestionnaires d'erreurs personnalisés
handler404 = "core.error_views.custom_404_view"
handler500 = "core.error_views.custom_500_view"
