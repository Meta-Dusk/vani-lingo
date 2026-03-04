from collections.abc import Mapping
from dataclasses import field, fields

class DataclassMappingMixin(Mapping):
    """Adds dict-like unpacking and access to any dataclass."""
    
    def __getitem__(self, key):
        return getattr(self, key)

    def __iter__(self):
        return iter(self.__dict__)

    def __len__(self):
        return len(self.__dict__)