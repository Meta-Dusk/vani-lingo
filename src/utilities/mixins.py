from collections.abc import Mapping
from dataclasses import fields

class DataclassMappingMixin(Mapping):
    """Adds dict-like unpacking and access to any dataclass."""
    
    def __getitem__(self, key):
        field_names = {f.name for f in fields(self)}
        if key in field_names:
            return getattr(self, key)
        raise KeyError(key)
    
    def __iter__(self):
        for f in fields(self):
            yield f.name
            
    def __len__(self):
        return len(self.__dict__)

class DebugMixin:
    def _on_debug_print(self, debug_msg: str) -> None:
        pass
    
    def _debug_print(self, msg: str) -> None:
        print(f"[{self.__class__.__name__}]: {msg}")
        self._on_debug_print(msg)