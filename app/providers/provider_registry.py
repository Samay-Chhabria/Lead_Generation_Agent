"""Provider registry.

Holds the set of available provider implementations keyed by name. Providers
register themselves here so the rest of the application can resolve providers
by name without knowing their concrete classes. Duplicate names are rejected
and names are validated before registration.
"""

import logging

from app.config.logging_config import get_logger
from app.exceptions.provider_exception import DuplicateProviderError, UnknownProviderError
from app.providers.base_provider import BaseProvider


class ProviderRegistry:
    """Registry of provider implementations keyed by provider name."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._providers: dict[str, type[BaseProvider]] = {}
        self._logger = logger or get_logger("provider")

    def register(
        self,
        provider_class: type[BaseProvider],
        name: str | None = None,
    ) -> None:
        """Register a provider class under its canonical name.

        Args:
            provider_class: A subclass of BaseProvider.
            name: Optional explicit name; defaults to provider_class.name.

        Raises:
            TypeError: When provider_class is not a BaseProvider subclass.
            ValueError: When the provider name is empty.
            DuplicateProviderError: When the name is already registered.
        """
        if not issubclass(provider_class, BaseProvider):
            raise TypeError(f"'{provider_class.__name__}' is not a BaseProvider subclass.")
        provider_name = name or provider_class.name
        if not isinstance(provider_name, str) or not provider_name.strip():
            raise ValueError("Provider name must be a non-empty string.")
        provider_name = provider_name.strip().lower()
        if provider_name in self._providers:
            raise DuplicateProviderError(f"Provider '{provider_name}' is already registered.")
        self._providers[provider_name] = provider_class
        self._logger.info("Provider registered: %s", provider_name)

    def get(self, name: str) -> type[BaseProvider]:
        """Return the provider class registered under a name.

        Raises:
            UnknownProviderError: When no provider is registered under the name.
        """
        key = name.strip().lower()
        if key not in self._providers:
            registered = ", ".join(self.list()) or "none"
            raise UnknownProviderError(
                f"Unknown provider '{name}'. Registered providers: {registered}."
            )
        return self._providers[key]

    def list(self) -> tuple[str, ...]:
        """Return the registered provider names, sorted."""
        return tuple(sorted(self._providers))

    def is_registered(self, name: str) -> bool:
        """Return True when a provider is registered under the name."""
        return name.strip().lower() in self._providers

    def unregister(self, name: str) -> None:
        """Remove a registered provider, if present."""
        key = name.strip().lower()
        if key in self._providers:
            del self._providers[key]
            self._logger.info("Provider unregistered: %s", key)

    def clear(self) -> None:
        """Remove all registered providers."""
        self._providers.clear()


provider_registry = ProviderRegistry()
