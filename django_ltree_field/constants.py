from __future__ import annotations

import enum


class LTreeTrigger(enum.Enum):
    """
    LTreeTrigger is an enumeration that defines the types of triggers
    that can be applied to an LTree field in a database.

    Attributes
    ----------
    PROTECT : str
        Prevents deletion or modification of a node if it has children.
    CASCADE : str
        Automatically propagates deletion or modification to child nodes.
    """

    PROTECT = "PROTECT"
    CASCADE = "CASCADE"
