from __future__ import annotations

import enum

from django.utils.translation import gettext_lazy as _


class LTreeTrigger(enum.Enum):
    PROTECT = "PROTECT"
    CASCADE = "CASCADE"
