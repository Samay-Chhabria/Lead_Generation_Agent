"""Centralized application constants.

Constants shared across the application live here so that values are never
hardcoded in business logic modules. Future constants should be added to this
module instead of being scattered through the codebase.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

APP_LOGGER_NAME = "lead_generation_agent"
CONSOLE_HANDLER_NAME = "console"
FILE_HANDLER_NAME = "file"

DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs"
DEFAULT_LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE_NAME = "application.log"
LOG_FILE_MAX_BYTES = 5 * 1024 * 1024
LOG_FILE_BACKUP_COUNT = 3

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

DEFAULT_LOG_LEVEL = "INFO"
VALID_LOG_LEVELS = ("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG")

DEFAULT_HEADLESS = True
DEFAULT_TIMEOUT = 30_000
DEFAULT_SLOW_MO = 300
DEFAULT_MAX_LEADS = 5
DEFAULT_SEARCH_PROVIDER = "google"
SUPPORTED_PROVIDERS = ("google", "google_maps", "bing_maps", "yellow_pages", "yelp")

DEFAULT_BROWSER_TYPE = "chromium"
SUPPORTED_BROWSERS = ("chromium", "firefox", "webkit")

# --- FreeLLM Router gateway (the only LLM the application uses) --------------
#
# The whole application talks to a single OpenAI-compatible gateway exposed by a
# FreeLLM Router instance (``FREELLM_BASE_URL``) and asks for ``model="auto"``
# on every request. The router performs all model selection, retries, provider
# rotation, fallback, rate-limit recovery, and load balancing; the application
# implements no client-side fallback chain and never names a concrete model.
FREELLM_PROVIDER_NAME = "freellm"
FREELLM_BASE_URL_ENV = "FREELLM_BASE_URL"
FREELLM_API_KEY_ENV = "FREELLM_API_KEY"
LLM_MODEL_ENV = "LLM_MODEL"

DEFAULT_LLM_ENABLED = True
DEFAULT_LLM_MODEL = "auto"
DEFAULT_FREELLM_BASE_URL = "http://localhost:3001/v1"

# Network-only retry policy. Only transient connection failures (connection
# refused, DNS failure, socket timeouts) are retried locally — with the same
# ``model="auto"`` request, never a different model. The sleep in seconds
# before retries 1, 2, ... is 2s then 4s.
DEFAULT_LLM_NETWORK_MAX_RETRIES = 2
DEFAULT_LLM_NETWORK_RETRY_BACKOFF = (2, 4)
DEFAULT_LLM_REQUEST_TIMEOUT = 30

DEFAULT_LLM_MAX_TOKENS = 2048
DEFAULT_LLM_TEMPERATURE = 0.0

# --- LLM providers ------------------------------------------------------------
DEFAULT_LLM_PROVIDER = "freellm"
SUPPORTED_LLM_PROVIDERS = ("mock", "freellm")
# Legacy spellings of the unified gateway are normalized to ``freellm`` when
# ``LLM_PROVIDER`` is set, so existing ``.env`` files keep working.
LLM_PROVIDER_ALIASES = {
    "freellmrouter": "freellm",
    "free_llm_router": "freellm",
}
