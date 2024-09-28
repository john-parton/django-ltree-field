from django.core import validators
from django.utils.translation import gettext_lazy as _

# Limit of 255 was raised in some newer version of postgres
label_validator = validators.RegexValidator(
    r"^[A-Za-z0-9_]{1,255}$",
    # TODO Better message?
    message=_(
        "Each label must consist of only the characters a-z, A-Z, 0-9, and underscores."
    ),
    code="invalid_ltree_label",
)
