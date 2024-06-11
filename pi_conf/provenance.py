import inspect
import logging
import os
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

log = logging.getLogger(__name__)

PROVENANCE_DEPTH = 2

class ProvenanceOp(str, Enum):
    set = "set"
    update = "update"
    clear = "clear"
    clear_and_set = "clear_and_set"

    def __str__(self):
        return self.value

class Provenance:
    """Provenance of the config"""

    def __init__(self, source: str, operation: str, stack: Optional[list[str]] = None):
        self.source = source
        self.stack = stack
        self.operation = operation
        if self.stack is None:
            self.stack = _provenance_manager.get_methods_that_called_this_method(PROVENANCE_DEPTH)

    def __repr__(self):
        return f"<Provenance: abbr_stack='{self.stack}' source='{self.source}' op='{self.operation}'>"

    def __str__(self):
        return f"<Provenance: abbr_stack='{self.stack}' source='{self.source}'> op='{self.operation}'"


@dataclass
class ProvenanceManager:
    """Provenance manager"""

    _provenance: dict[int, list[Provenance]] = field(default_factory=lambda: defaultdict(list))
    _enabled: set[int] = field(default_factory=set)

    def set_enabled(self, obj, enable: bool = True):
        """Set whether or not to enable provenance"""
        if enable:
            self._enabled.add(id(obj))
        else:
            self._enabled.discard(id(obj))

    def get(self, obj) -> list[Provenance]:
        """Get the provenance of the given object"""
        return self._provenance.get(id(obj), [])

    def set(self, obj, provenance: list[Provenance]):
        """Set the provenance of the given object"""
        oid = id(obj)
        if oid not in self._enabled:
            return
        if isinstance(provenance, Provenance):
            provenance = [provenance]
        self._provenance[oid] = provenance

    def append(self, obj, provenance: Provenance):
        """Append to the provenance of the given object"""
        oid = id(obj)
        if oid not in self._enabled:
            return
        self._provenance[oid].append(provenance)

    def extend(self, obj, provenance: list[Provenance]):
        """Extend the provenance of the given object"""
        oid = id(obj)
        if oid not in self._enabled:
            return
        self._provenance[id(obj)].extend(provenance)

    def clear(self, obj):
        """Clear the provenance of the given object"""
        oid = id(obj)
        if oid not in self._enabled:
            return
        self._provenance[id(obj)] = []

    def __repr__(self):
        return f"<ProvenanceManager: {self._provenance}>"

    def delete(self, obj):
        """Delete the provenance of the given object"""
        try:
            del self._provenance[id(obj)]
        except KeyError:
            pass

    @staticmethod
    def get_methods_that_called_this_method(depth: Optional[int] = None) -> str:
        """Get the method that called this method"""
        try:
            stack = []
            for i in range(len(inspect.stack())):
                frame = inspect.stack()[i]
                lineno = frame.lineno
                module_path = frame.filename
                base_name = os.path.basename(module_path)
                n = os.path.basename(os.path.dirname(module_path))
                if n == "pi_conf":
                    continue
                fn = frame.function
                stack.append(f"{base_name}::{fn}:{lineno}")
            if depth is not None:
                return stack[-depth:][::-1]
            return stack[::-1]

        except Exception as e:
            log.error(f"Error! {e}")
            return "Unknown"


@dataclass
class NullOpProvenanceManager(ProvenanceManager):
    """Null op provenance manager"""

    def set_enabled(self, obj, enable: bool = True):
        pass

    def get(self, obj) -> list[Provenance]:
        """Get the provenance of the given object"""
        return []

    def set(self, obj, provenance: list[Provenance]):
        """Set the provenance of the given object"""

    def append(self, obj, provenance: Provenance):
        """Append to the provenance of the given object"""

    def extend(self, obj, provenance: list[Provenance]):
        """Extend the provenance of the given object"""

    def clear(self, obj):
        """Clear the provenance of the given object"""

    def __repr__(self):
        return f"<NullOpProvenanceManager>"

    def delete(self, obj):
        """Delete the provenance of the given object"""

    @staticmethod
    def get_methods_that_called_this_method(depth: Optional[int] = None) -> str:
        """Get the method that called this method"""
        return "Unknown"


_provenance_manager = ProvenanceManager()  ## provenance of the config


def set_use_provenance(use_provenance: bool = True):
    """Set whether or not to use provenance"""
    global _provenance_manager
    if use_provenance:
        _provenance_manager = ProvenanceManager()
    else:
        _provenance_manager = NullOpProvenanceManager()


def get_provenance_manager() -> ProvenanceManager:
    """Get the provenance manager"""
    return _provenance_manager
