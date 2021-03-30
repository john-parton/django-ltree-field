from django.contrib import admin
from django_ltree_field.test_utils.test_app import models as test_models


@admin.register(test_models.SimpleNode)
class SimpleNodeAdmin(admin.ModelAdmin):
    pass
