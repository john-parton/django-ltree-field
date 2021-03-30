from django.core import validators
from django.utils.translation import gettext_lazy as _


label_validator = validators.RegexValidator(
    r'^[A-Za-z0-9_]{1,255}$',
    # TODO Better message
    message=_("Each label must consist of only the characters a-z, A-Z, 0-9, and underscores."),
    # message=_("Each label must consist of only the characters a-z, A-Z, 0-9, and underscores, with a total length between 1 and 255."),
    code='invalid_ltree_label',
)
