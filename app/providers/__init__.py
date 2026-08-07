"""Search provider package.

Every supported provider is registered by its canonical name. The Google Maps
provider is fully implemented; Bing Maps, Yellow Pages, and Yelp are registered
as clean, documented extension points (see each module) that inherit the shared
provider contract. Adding a new provider is therefore a single step: subclass
``SearchProvider``, implement ``search()``/``collect_results()``, and register
the class here — no pipeline or agent code changes.
"""

from app.config.constants import SUPPORTED_PROVIDERS
from app.providers.base_provider import BaseProvider
from app.providers.bing_maps_provider import BingMapsProvider
from app.providers.google_maps_provider import GoogleMapsProvider
from app.providers.provider_factory import ProviderFactory
from app.providers.provider_registry import ProviderRegistry, provider_registry
from app.providers.provider_result import ProviderResult
from app.providers.search_provider import SearchProvider
from app.providers.yellow_pages_provider import YellowPagesProvider
from app.providers.yelp_provider import YelpProvider

_PROVIDER_CLASSES = {
    "google": GoogleMapsProvider,
    "google_maps": GoogleMapsProvider,
    "bing_maps": BingMapsProvider,
    "yellow_pages": YellowPagesProvider,
    "yelp": YelpProvider,
}

for _provider_name in SUPPORTED_PROVIDERS:
    provider_registry.register(_PROVIDER_CLASSES[_provider_name], name=_provider_name)

__all__ = [
    "BaseProvider",
    "BingMapsProvider",
    "GoogleMapsProvider",
    "ProviderFactory",
    "ProviderRegistry",
    "ProviderResult",
    "SearchProvider",
    "YellowPagesProvider",
    "YelpProvider",
    "provider_registry",
]
