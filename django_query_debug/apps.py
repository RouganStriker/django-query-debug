from django.apps import AppConfig
from django.conf import settings

from django_query_debug.patch import PatchDjangoDescriptors


class DjangoQueryDebugConfig(AppConfig):
    name = "django_query_debug"

    def ready(self):
        if getattr(settings, "ENABLE_QUERY_WARNINGS", False):
            # Apply patch
            PatchDjangoDescriptors()
