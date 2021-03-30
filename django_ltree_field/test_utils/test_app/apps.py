from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TestAppConfig(AppConfig):
    name = 'django_ltree_field.test_utils.test_app'
    verbose_name = _("Test App")
