"""
Storage backend base classes and registry.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from pydantic import AnyUrl, TypeAdapter

from earnings_calendar.exceptions import StorageError

_URL_ADAPTER = TypeAdapter(AnyUrl)


class StorageBackend(ABC):
    """
    Base class for storage backends selected via URL schemes.
    """

    scheme: ClassVar[str | None] = None
    _registry: ClassVar[dict[str, type[StorageBackend]]] = {}

    def __init_subclass__(cls, **kwargs) -> None:
        """
        Register subclasses that declare a storage scheme.
        """
        super().__init_subclass__(**kwargs)
        scheme = getattr(cls, "scheme", None)
        if scheme:
            StorageBackend._registry[scheme] = cls

    def __init__(self, location: AnyUrl) -> None:
        """
        Store the raw storage location for this backend.
        """
        self.location = location

    @classmethod
    def from_location(cls, location: AnyUrl | str) -> StorageBackend:
        """
        Select a backend based on the storage URL scheme.
        """
        resolved: AnyUrl = _URL_ADAPTER.validate_python(str(location))

        scheme = resolved.scheme.lower()

        backend = cls._registry.get(scheme)
        if backend is None:
            raise StorageError(f"unsupported storage scheme: {scheme}")

        return backend(resolved)

    @abstractmethod
    def prepare(self) -> Path:
        """
        Prepare local storage and return the on-disk SQLite path.
        """

    @abstractmethod
    def finalize(self) -> None:
        """
        Persist any changes and release temporary resources.
        """
