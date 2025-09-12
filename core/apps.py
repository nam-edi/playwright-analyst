from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        """Importe les vues d'admin personnalisées au démarrage"""
        from . import admin_views  # noqa: F401
