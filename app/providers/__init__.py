"""Search provider package.

Auto-registers the concrete Google Maps provider for the 'google' and
'google_maps' names, and a placeholder provider for the remaining supported
names. Concrete providers replace placeholders in future milestones by
unregistering the name and registering their own class.
"""

from app.config.constants import SUPPORTED_PROVIDERS
from app.providers.base_provider import BaseProvider
from app.providers.google_maps_provider import GoogleMapsProvider
from app.providers.provider_factory import ProviderFactory
from app.providers.provider_registry import ProviderRegistry, provider_registry
from app.providers.provider_result import ProviderResult
from app.providers.search_provider import SearchProvider

_MAPS_PROVIDER_NAMES = frozenset({"google", "google_maps"})

for _provider_name in SUPPORTED_PROVIDERS:
    provider_class = (
        GoogleMapsProvider if _provider_name in _MAPS_PROVIDER_NAMES else SearchProvider
    )
    provider_registry.register(provider_class, name=_provider_name)

__all__ = [
    "BaseProvider",
    "GoogleMapsProvider",
    "ProviderFactory",
    "ProviderRegistry",
    "ProviderResult",
    "SearchProvider",
    "provider_registry",
]
