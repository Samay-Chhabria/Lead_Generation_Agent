"""Application orchestration.

Owns the application lifecycle: loading and validating configuration,
initializing logging, starting the agent, and shutting down cleanly.
Unexpected failures are caught, logged, and translated into a non-zero exit
code.
"""

from app.agent.lead_generation_agent import LeadGenerationAgent
from app.config.logging_config import configure_logging, get_logger
from app.config.settings import Settings
from app.providers.provider_factory import ProviderFactory


class LeadGenerationApplication:
    """Coordinates the application lifecycle."""

    def __init__(
        self,
        settings: Settings | None = None,
        factory: ProviderFactory | None = None,
    ) -> None:
        self._settings = settings
        self._factory = factory
        self._logger = get_logger()

    def run(self, prompt: str | None = None) -> int:
        """Start the application and return the process exit code.

        Args:
            prompt: Optional prompt for programmatic callers. When omitted (the
                normal CLI path), the agent reads the prompt from the console.
        """
        try:
            if self._settings is None:
                self._settings = Settings.from_env()
            self._settings.prepare()
            configure_logging(self._settings)

            self._logger.info("Application starting...")
            self._logger.info("Loading configuration...")
            self._logger.info("Logging initialized.")

            agent = LeadGenerationAgent(
                settings=self._settings,
                logger=self._logger,
                factory=self._factory,
            )
            result = agent.run(prompt)
            if result.success:
                return 0
            return 1
        except Exception as exc:
            self._logger.exception("Application failed: %s", exc)
            return 1
        finally:
            self._logger.info("Application shutting down...")
