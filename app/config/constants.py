"""Centralized application constants.

Constants shared across the application live here so that values are never
hardcoded in business logic modules. Future constants should be added to this
module instead of being scattered through the codebase.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

APP_NAME = "Lead Generation Agent"
APP_VERSION = "0.1.0"

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
DEFAULT_MAX_LEADS = 25
DEFAULT_SEARCH_PROVIDER = "google"
SUPPORTED_PROVIDERS = ("google", "google_maps", "bing_maps", "yellow_pages", "yelp")

DEFAULT_BROWSER_TYPE = "chromium"
SUPPORTED_BROWSERS = ("chromium", "firefox", "webkit")
DEFAULT_PAGE_URL = "about:blank"
