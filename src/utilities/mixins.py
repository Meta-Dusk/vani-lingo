from collections.abc import Mapping

class DataclassMappingMixin(Mapping):
    """Adds dict-like unpacking and access to any dataclass."""
    
    def __getitem__(self, key):
        return getattr(self, key)

    def __iter__(self):
        return iter(self.__dict__)

    def __len__(self):
        return len(self.__dict__)

class DebugMixin:
    def _on_debug_print(self, debug_msg: str) -> None:
        pass
    
    def _debug_print(self, msg: str) -> None:
        print(f"[{self.__class__.__name__}]: {msg}")
        self._on_debug_print(msg)