from __future__ import annotations

import enum


class LTreeTrigger(enum.Enum):
    """Control the behavior of triggers for LTree fields.

    Attributes
    ----------
    PROTECT : str
        Prevents deletion or modification of a node if it has children.
    CASCADE : str
        Automatically propagates deletion or modification to child nodes.
    """

    PROTECT = "PROTECT"
    CASCADE = "CASCADE"
