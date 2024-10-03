from django.contrib.postgres.indexes import GistIndex
from django.db import models

from django_ltree_field.fields import LTreeField


# See https://www.postgresql.org/docs/17/ltree.html#LTREE-INDEXES
# gist_ltree_ops GiST opclass approximates a set of path labels as a bitmap signature. 
# Its optional integer parameter siglen determines the signature length in bytes. 
# The default signature length is 8 bytes. The length must be a positive multiple of int 
# alignment (4 bytes on most machines)) up to 2024. Longer signatures lead to a more
# precise search (scanning a smaller fraction of the index and fewer heap pages), at the cost of a larger index.

# Example of creating such an index with the default signature length of 8 bytes:

# CREATE INDEX path_gist_idx ON test USING GIST (path);

# Example of creating such an index with a signature length of 100 bytes:

# CREATE INDEX path_gist_idx ON test USING GIST (path gist_ltree_ops(siglen=100));


opclass [ ( opclass_parameter = value [, ... ] ) ] 



class LtreeGistIndex(GistIndex):

    def __init__(self, *expressions, siglen=None, **kwargs):
        self.siglen = siglen
        super().__init__(*expressions, **kwargs)

    def deconstruct(self):
        path, args, kwargs = super().deconstruct()
        if self.siglen is not None:
            kwargs["siglen"] = self.siglen
        return path, args, kwargs

    def get_with_params(self):
        with_params = []
        if self.buffering is not None:
            with_params.append("buffering = %s" % ("on" if self.buffering else "off"))
        if self.fillfactor is not None:
            with_params.append("fillfactor = %d" % self.fillfactor)
        return with_params