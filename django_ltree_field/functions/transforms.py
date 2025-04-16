from __future__ import annotations

from django.db import models
from django.db.models import Transform


class NLevel(Transform):
    # "depth" is slightly more usable than "nlevel"
    # And less confusing than "len"
    # Might be more generic if support for a backend other than postgres were ever added
    # If that backend uses a different function
    lookup_name = "depth"
    function = "nlevel"
    output_field = models.PositiveIntegerField()  # type: ignore[assignment]
