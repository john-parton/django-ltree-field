default_app_config = 'django_ltree_field.apps.DjangoLTreeFieldConfig'

try:
    from .version import version as __version__
# Should this raise?
except ImportError:
    pass
