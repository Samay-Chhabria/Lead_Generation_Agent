"""Google Maps search provider.

GoogleMapsProvider is a state-machine driven provider. It drives a real browser
session through discrete states - navigation, consent, search, results,
collection, extraction, and export - retrying each state before failing. The
search query comes from the SearchPlan, business listings are discovered with
the ResultCollector, and each listing is opened to extract a structured Lead.
Extraction failures for one business never stop the remaining businesses.

Robustness contract
-------------------
The provider never trusts a single locator. The Google Maps search input is
resolved through a layered, actionability-verified strategy and re-resolved
fresh immediately before every interaction, because Google's SPA re-renders
the omnibox after text is typed (the server-rendered ``input#ucc-1`` /
``input[name=q]`` is replaced by the app's own ``#searchboxinput`` or a
re-rendered input without a label association). No locator is ever cached
across interactions: a stale locator makes ``fill()`` hang, so every
fill/click/press works on a freshly resolved box, ``fill()`` falls back to
click -> Ctrl+A -> type(delay=40) -> Enter instead of retrying the same broken
interaction, and after Enter the provider waits event-driven for one of (URL
change, results feed, box value == query, network idle). Consent dialogs are
scanned in every frame (including iframes) with regional text variants,
redirects away from Maps are recovered, and every failure writes HTML,
screenshots, frame/textbox diagnostics, and a diagnostic report before raising.
"""

import json
import logging
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.sync_api import Locator, Page

from app.browser.browser_manager import BrowserManager
from app.config.settings import Settings
from app.exceptions.provider_exception import (
    ProviderElementNotFoundError,
    ProviderNavigationError,
    ProviderSearchError,
)
from app.execution.execution_logger import get_execution_logger
from app.extractor.business_detail_extractor import BusinessDetailExtractor
from app.extractor.business_navigator import BusinessNavigator
from app.models.business_reference import BusinessReference
from app.models.lead import Lead
from app.models.search_plan import SearchPlan
from app.providers.base_provider import BaseProvider
from app.providers.result_collector import ResultCollector
from app.providers.result_selection import (
    DEFAULT_RESULT_LIMIT,
    candidate_budget,
    select_top,
)
from app.utils.helpers import ensure_directory

GOOGLE_MAPS_URL = "https://www.google.com/maps"

#: Ordered, layered search-input strategies. The canonical real inputs on the
#: full Google Maps site are ``#searchboxinput`` and the element with
#: ``aria-label="Search Google Maps"``. The lightweight/server-rendered shell
#: uses ``input[role="combobox"]`` / ``input[name="q"]``. Semantic locators
#: come after the specific CSS because ``get_by_label`` also matches the
#: server-rendered placeholder via its associated <label>, which is exactly
#: the locator that goes stale when the SPA re-renders the omnibox.
SEARCH_INPUT_SELECTORS = (
    "#searchboxinput",
    'input[aria-label="Search Google Maps"]',
    'input[role="combobox"]',
    'input[name="q"]',
    'input[aria-label*="Search"]',
    'input[aria-label*="search"]',
    'input[placeholder*="Search"]',
    'input[placeholder*="search"]',
    'input[type="text"]',
)

SEARCH_INPUT_SEMANTIC = (
    'get_by_label("Search Google Maps")',
    'get_by_role("combobox", name="Search Google Maps")',
    'get_by_placeholder("Search Google Maps")',
    'get_by_role("searchbox")',
)

RESULTS_CONTAINER_SELECTORS = (
    'div[role="feed"]',
    '[aria-label*="Results for"]',
    'div[role="main"]',
    "article",
    '[role="article"]',
)

SEARCH_BUTTON_SELECTORS = (
    "#searchbox-searchbutton",
    'button[aria-label="Search"]',
    'button[aria-label*="Search"]',
    'button[jsaction*="searchbox"]',
)

#: DOM predicate evaluated (event-driven, no polling) after Enter is pressed.
#: Returns True as soon as the submission has clearly landed: the URL moved to
#: the results route, a results feed rendered, or the search box holds the
#: query as its value. Network-idle is checked separately via
#: wait_for_load_state, so it does not need a DOM predicate.
SUBMISSION_LANDED_JS = """\
(q) => {
  if (location.href && location.href.indexOf('/maps/search/') !== -1) return true;
  const feed = document.querySelector(
    'div[role="feed"], [aria-label*="Results for"], [role="article"]'
  );
  if (feed) return true;
  const box = document.querySelector(
    '#searchboxinput, input[aria-label="Search Google Maps"], ' +
    'input[role="combobox"], input[name="q"]'
  );
  return !!(box && box.value === q);
}
"""

CONSENT_BUTTON_TEXTS = (
    "Accept all",
    "Accept",
    "I agree",
    "Agree",
    "Continue",
    "Accept cookies",
    "Reject all",
    "Alle akzeptieren",
    "Tout accepter",
    "Aceptar todo",
    "Aceptar",
    "Accetta tutto",
    "Accetta",
    "Accepteer alles",
    "Accepter",
    "Aceitar tudo",
    "Aceito",
    "同意",
    "同意する",
)

NAVIGATION_ATTEMPTS = 3
SEARCH_ATTEMPTS = 3
RESULTS_ATTEMPTS = 3
SETTLE_MS = 2_000
RETRY_DELAY_MS = 1_500
CLICK_TIMEOUT_MS = 3_000
BOOT_POLL_MS = 500
SELECTOR_PROBE_TIMEOUT_MS = 1_500

#: Provider states mapped onto the user-facing timeline phase names.
_PHASE_BY_STATE = {
    "Navigation": "Navigating",
    "Search": "Searching",
    "Results": "Waiting For Results",
    "Collection": "Collecting Businesses",
    "Extraction": "Extracting Details",
    "Export": "Saving Excel",
}

DEBUG_DIR = Path("debug")

SUPPLEMENTAL_SELECTORS = {
    "rating": (
        'div[role="img"][aria-label*="stars"]',
        '[aria-label*="stars"]',
        '[data-attrid="rating"]',
    ),
    "reviews": (
        'button[aria-label*="reviews"]',
        'span[aria-label*="reviews"]',
        'span:has-text("reviews")',
    ),
    "category": (
        '[data-attrid="subtitle"]',
        'button[data-item-id="category"]',
        '[aria-label*="category"]',
    ),
    "working_hours": (
        '[data-item-id="oh"]',
        'button[data-item-id="hours"]',
        'div[data-attrid*="hours"]',
        '[aria-label*="hours"]',
    ),
}


class GoogleMapsProvider(BaseProvider):
    """Search Google Maps for businesses described by a SearchPlan.

    The provider moves through a fixed sequence of states. Every state logs its
    transition, captures screenshots, HTML, frame/textbox diagnostics, and a
    diagnostic report into the debug folder, and retries before it is allowed
    to fail. A failure in extraction for a single business is logged and
    skipped; all other states raise their typed exception only after every
    retry has been exhausted.
    """

    name = "google_maps"

    def __init__(
        self,
        browser: BrowserManager,
        plan: SearchPlan,
        settings: Settings,
        logger: logging.Logger | None = None,
        navigator: BusinessNavigator | None = None,
        extractor: BusinessDetailExtractor | None = None,
    ) -> None:
        super().__init__(browser, plan, settings, logger)
        self._page: Page | None = None
        self._references: list[BusinessReference] = []
        self._leads: list[Lead] = []
        self._details: list[dict[str, str]] = []
        self._navigator = navigator
        self._extractor = extractor
        self._debug_dir = DEBUG_DIR

    @property
    def page(self) -> Page | None:
        """Return the page the provider is working on, if any."""
        return self._page

    @property
    def references(self) -> list[BusinessReference]:
        """Return the business references discovered by the last search."""
        return list(self._references)

    @property
    def leads(self) -> list[Lead]:
        """Return the leads extracted from the last search's references."""
        return list(self._leads)

    @property
    def details(self) -> list[dict[str, str]]:
        """Return supplemental details (rating, reviews, hours) per lead."""
        return list(self._details)

    def initialize(self) -> None:
        """Launch the browser (if needed), create a page, and prepare debugging."""
        exec_log = get_execution_logger()
        if not self._browser.is_running():
            exec_log.launching_browser()
            launch_started = time.perf_counter()
            self._browser.launch()
            exec_log.timing("browser_launch", time.perf_counter() - launch_started)
        self._page = self._browser.new_page()
        self._page.set_default_timeout(self._settings.timeout)
        ensure_directory(self._debug_dir)
        self._verify_active_page()
        self._logger.info("Provider initialized successfully.")

    def search(self) -> list[str]:
        """Drive the provider through every state in order.

        Returns:
            An empty list: business page URLs are collected in a later
            milestone. The discovered references and extracted leads are
            available via the `references`, `leads`, and `details` properties.

        Raises:
            ProviderNavigationError: When Google Maps cannot be opened.
            ProviderElementNotFoundError: When the search input is missing.
            ProviderSearchError: When the search cannot be submitted or the
                results never load.
        """
        page = self._require_page()
        self._logger.info("Searching %s", self.query)

        self._enter_state("Navigation")
        self._open_maps(page)
        self._logger.info("Navigation Complete.")

        self._enter_state("Consent")
        self._handle_consent(page)

        self._enter_state("Search")
        last_error: Exception | None = None
        for attempt in range(1, SEARCH_ATTEMPTS + 1):
            try:
                if not self._submit_query(page):
                    raise ProviderSearchError(f"Failed to submit search '{self.query}'.")
                self._enter_state("Results")
                self._wait_for_results(page)
                last_error = None
                break
            except ProviderElementNotFoundError:
                raise
            except ProviderSearchError as exc:
                last_error = exc
                self._logger.warning(
                    "Search+results attempt %d/%d failed: %s",
                    attempt,
                    SEARCH_ATTEMPTS,
                    exc,
                )
                page.wait_for_timeout(RETRY_DELAY_MS)
        if last_error is not None:
            self._capture_diagnostics(page, "error")
            self._write_diagnostic_report(page, f"search or results never succeeded: {last_error}")
            raise ProviderSearchError(f"Search failed for '{self.query}': {last_error}")

        self._enter_state("Collection")
        self._collect_businesses(page)
        self._rank_and_select()

        self._enter_state("Extraction")
        self._extract_business(page)

        self._enter_state("Export")
        self._export()

        self._logger.info("Search completed.")
        return []

    def collect_results(self) -> list[Any]:
        """Verify that results loaded and return the discovered references."""
        page = self._require_page()
        if any(page.locator(selector).count() > 0 for selector in RESULTS_CONTAINER_SELECTORS):
            self._logger.info("Results loaded successfully.")
            return list(self._references)
        self._logger.warning("Results container not visible; no results to collect.")
        return list(self._references)

    def close(self) -> None:
        """Release the page created by this provider.

        The browser is owned by the provider factory and is closed by the
        pipeline, so this method never touches it.
        """
        page, self._page = self._page, None
        if page is not None and not page.is_closed():
            try:
                page.close()
                self._logger.info("Provider page closed.")
            except Exception as exc:
                self._logger.warning("Failed to close provider page: %s", exc)
        self._logger.info("Provider closed.")

    def _require_page(self) -> Page:
        page = self._page
        if page is None or page.is_closed():
            raise ProviderSearchError(
                "No active page is available; call initialize() before searching."
            )
        return page

    def _enter_state(self, state: str) -> None:
        """Log that the provider is entering a new state."""
        self._logger.info("Entering %s State...", state)
        phase = _PHASE_BY_STATE.get(state)
        if phase is not None:
            get_execution_logger().phase(phase)

    # ------------------------------------------------------------------ #
    # Navigation
    # ------------------------------------------------------------------ #

    def _open_maps(self, page: Page) -> None:
        """Open Google Maps, recover from redirects, and wait for the SPA to
        render the search UI.

        Navigation waits on the load event only; networkidle is never used.
        Every attempt captures a screenshot, HTML, and frame/textbox
        diagnostics before completing.
        """
        self._logger.info("Opening Google Maps.")
        last_error: Exception | None = None
        for attempt in range(1, NAVIGATION_ATTEMPTS + 1):
            try:
                page.goto(
                    GOOGLE_MAPS_URL,
                    wait_until="domcontentloaded",
                    timeout=self._settings.timeout,
                )
                page.wait_for_load_state("load", timeout=self._settings.timeout)
                self._recover_redirect(page)
                self._wait_for_app_boot(page)
                self._logger.info("Page title: %s", page.title())
                self._logger.info("Current URL: %s", page.url)
                self._capture_diagnostics(page, "navigation")
                self._logger.info("Google Maps opened.")
                return
            except Exception as exc:
                last_error = exc
                self._logger.warning(
                    "Navigation attempt %d/%d failed: %s", attempt, NAVIGATION_ATTEMPTS, exc
                )
                page.wait_for_timeout(RETRY_DELAY_MS)
        self._capture_diagnostics(page, "error")
        self._write_diagnostic_report(page, f"could not open Google Maps: {last_error}")
        raise ProviderNavigationError(f"Could not open Google Maps: {last_error}")

    def _recover_redirect(self, page: Page) -> None:
        """If Google redirected away from Maps (consent, accounts, homepage),
        dismiss any consent UI and return to Maps."""
        try:
            url = page.url or ""
        except Exception:
            return
        if not url.startswith("http") or "maps" in url:
            return
        self._logger.warning("Redirected away from Maps to '%s'; recovering.", url)
        self._handle_consent(page)
        page.goto(
            GOOGLE_MAPS_URL,
            wait_until="domcontentloaded",
            timeout=self._settings.timeout,
        )
        page.wait_for_load_state("load", timeout=self._settings.timeout)

    def _wait_for_app_boot(self, page: Page) -> None:
        """Wait until any search-input strategy matches, signalling that the
        Maps SPA has rendered its search UI."""
        timeout_seconds = max(self._settings.timeout / 1000.0, 5.0)
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            for description, _locator in self._search_strategies(page):
                try:
                    if _locator.count() > 0:
                        self._logger.info("Search UI rendered (matched '%s').", description)
                        return
                except Exception:
                    continue
            page.wait_for_timeout(BOOT_POLL_MS)
        self._logger.warning(
            "Search UI did not render within %.1fs; continuing anyway.", timeout_seconds
        )

    # ------------------------------------------------------------------ #
    # Consent
    # ------------------------------------------------------------------ #

    def _handle_consent(self, page: Page) -> bool:
        """Detect and accept any consent dialog across every frame.

        Each known button label is tried with semantic and CSS locators in the
        main frame and all iframes. A missing dialog is not an error: the state
        simply completes. Returns True when a dialog was accepted.
        """
        self._logger.info("Checking for consent dialogs (main frame + iframes)...")
        for text in CONSENT_BUTTON_TEXTS:
            if self._click_consent_button(page, text):
                self._logger.info("Consent dialog accepted via '%s'.", text)
                page.wait_for_timeout(SETTLE_MS)
                return True
        if self._accept_standalone_consent(page):
            return True
        self._logger.info("No consent dialog detected; continuing.")
        return False

    def _click_consent_button(self, page: Page, text: str) -> bool:
        """Try to click a button matching the given text in every frame."""
        for frame in self._iter_frames(page):
            candidates = [
                frame.get_by_role("button", name=text, exact=True),
                frame.get_by_role("button", name=text),
                frame.locator(f'button:has-text("{text}")'),
                frame.locator(f'[role="button"]:has-text("{text}")'),
                frame.locator(f'form input[type="submit"][value*="{text}"]'),
            ]
            for locator in candidates:
                try:
                    if locator.count() == 0:
                        continue
                    first = locator.first
                    if self._is_definitely_hidden(first):
                        continue
                    first.click(timeout=CLICK_TIMEOUT_MS)
                    return True
                except Exception as exc:
                    self._logger.debug(
                        "Consent locator for '%s' in %s not clickable: %s",
                        text,
                        self._frame_label(frame),
                        exc,
                    )
        return False

    def _accept_standalone_consent(self, page: Page) -> bool:
        """Dismiss a standalone consent.google.com page by clicking its form."""
        try:
            url = page.url or ""
        except Exception:
            return False
        if "consent.google.com" not in url:
            return False
        self._logger.info("Standalone Google consent page detected: %s", url)
        for frame in self._iter_frames(page):
            try:
                for locator in (frame.locator("form").first, frame.get_by_role("button").first):
                    try:
                        locator.click(timeout=CLICK_TIMEOUT_MS)
                        return True
                    except Exception:
                        continue
            except Exception:
                continue
        return False

    def _iter_frames(self, page: Page) -> list[Any]:
        """Return [main frame] + all child frames, or just the page itself."""
        try:
            return list(page.frames)
        except Exception:
            return [page]

    def _frame_label(self, frame: Any) -> str:
        name = getattr(frame, "name", None) or ""
        url = ""
        try:
            url = frame.url or ""
        except Exception:
            pass
        return f"frame(name={name!r}, url={url!r})"

    # ------------------------------------------------------------------ #
    # Search box resolution
    # ------------------------------------------------------------------ #

    def _search_strategies(self, page: Page) -> list[tuple[str, Locator]]:
        """Return ordered (description, locator) strategies for the search box."""
        strategies: list[tuple[str, Locator]] = [
            (selector, page.locator(selector)) for selector in SEARCH_INPUT_SELECTORS
        ]
        for label in SEARCH_INPUT_SEMANTIC:
            if label.startswith("get_by_label"):
                strategies.append((label, page.get_by_label("Search Google Maps")))
            elif "combobox" in label:
                strategies.append((label, page.get_by_role("combobox", name="Search Google Maps")))
            elif label.startswith("get_by_placeholder"):
                strategies.append((label, page.get_by_placeholder("Search Google Maps")))
            else:
                strategies.append((label, page.get_by_role("searchbox")))
        return strategies

    def _find_search_box(self, page: Page) -> Locator:
        """Locate an editable Google Maps search input.

        Every strategy is tested on every attempt and only a locator that
        verifies as visible, enabled, and editable is returned. Candidates are
        re-queried on each attempt because the SPA re-renders the omnibox and
        previously-matched locators can go stale.
        """
        strategies = self._search_strategies(page)
        for attempt in range(1, SEARCH_ATTEMPTS + 1):
            for description, locator in strategies:
                try:
                    if self._is_actionable_search_input(locator):
                        self._logger.info(
                            "Search box resolved via '%s' (attempt %d/%d).",
                            description,
                            attempt,
                            SEARCH_ATTEMPTS,
                        )
                        self._highlight(locator)
                        return locator
                except Exception as exc:
                    self._logger.debug("Strategy '%s' failed: %s", description, exc)
            self._logger.warning("Search box not found (attempt %d/%d).", attempt, SEARCH_ATTEMPTS)
            self._capture_diagnostics(page, "search_box")
            page.wait_for_timeout(RETRY_DELAY_MS)
        self._write_diagnostic_report(
            page, "search input was never found in a visible, enabled, editable state"
        )
        raise ProviderElementNotFoundError("Google Maps search input was not found.")

    def _reacquire_search_box(self, page: Page) -> Locator:
        """Re-resolve the search input fresh right before an interaction.

        Playwright locators go stale when Google's SPA re-renders the omnibox
        after text is typed, which makes a cached locator hang inside fill().
        Locators are therefore never stored and reused; every interaction calls
        this first.
        """
        return self._find_search_box(page)

    def _is_actionable_search_input(self, locator: Locator) -> bool:
        """Verify the locator is attached, visible, enabled, and editable.

        Checks that cannot run (missing methods on test doubles) are treated as
        unknown and do not reject the candidate; only definitive failures do.
        """
        if not self._locator_count(locator):
            return False
        first = locator.first
        if self._locator_check(first, "is_visible") is False:
            self._logger.debug("Search box candidate not visible; rejected.")
            return False
        if self._locator_check(first, "is_enabled") is False:
            self._logger.debug("Search box candidate disabled; rejected.")
            return False
        if self._locator_check(first, "is_editable") is False:
            self._logger.debug("Search box candidate not editable; rejected.")
            return False
        box = self._locator_bounding_box(first)
        if box is not None and (box.get("width", 0) <= 0 or box.get("height", 0) <= 0):
            self._logger.debug("Search box candidate has zero-size box; rejected.")
            return False
        self._focus_best_effort(first)
        return True

    def _ensure_fillable(self, page: Page, locator: Locator) -> bool:
        """Verify the box is visible, enabled, and editable right before fill.

        Logs the reason (``not visible`` / ``not enabled`` / ``not editable`` /
        zero-size box) when a check fails so a hang is never silent. Callers
        treat a rejection as a signal to re-resolve and type instead of
        retrying the same interaction.
        """
        reasons: list[str] = []
        if self._locator_check(locator, "is_visible") is False:
            reasons.append("not visible")
        if self._locator_check(locator, "is_enabled") is False:
            reasons.append("not enabled")
        if self._locator_check(locator, "is_editable") is False:
            reasons.append("not editable")
        box = self._locator_bounding_box(locator)
        if box is not None and (box.get("width", 0) <= 0 or box.get("height", 0) <= 0):
            reasons.append("zero-size bounding box")
        if reasons:
            self._logger.warning(
                "Search box cannot be filled: %s. Re-resolving and typing instead.",
                ", ".join(reasons),
            )
            return False
        return True

    def _submit_query(self, page: Page) -> bool:
        """Drive the search-submission micro state machine.

        Google's SPA re-renders the omnibox after text is typed, which can
        invalidate a locator resolved earlier and make ``fill()`` hang. The box
        is therefore re-resolved fresh immediately before every interaction and
        never cached across calls. Flow: LocateSearchBox -> FocusSearchBox ->
        EnterQuery -> SubmitQuery -> WaitForResults. If ``fill()`` is blocked,
        EnterQuery falls back to click -> Ctrl+A -> type(delay=40) -> Enter
        instead of retrying the same broken interaction.
        """
        self._logger.info("Submitting query...")
        self._save_screenshot(page, "before_fill.png")
        self._save_html(page, "before_fill.html")
        try:
            self._enter_state("LocateSearchBox")
            box = self._reacquire_search_box(page)
            self._enter_state("FocusSearchBox")
            self._focus_search_box_state(page, box)
            self._enter_state("EnterQuery")
            entry = self._enter_query_state(page, box)
            if not entry:
                raise ProviderSearchError("The query text could not be entered.")
            self._save_screenshot(page, "after_fill.png")
            if entry == "filled":
                self._enter_state("SubmitQuery")
                if not self._submit_query_state(page):
                    raise ProviderSearchError("Enter could not be dispatched.")
            self._save_screenshot(page, "after_enter.png")
            self._wait_for_submission(page)
            self._logger.info("Query submitted: %s", self.query)
            return True
        except ProviderElementNotFoundError:
            raise
        except Exception as exc:
            self._log_playwright_error("Query submission failed", exc)
        self._save_screenshot(page, "submit_failure.png")
        self._save_html(page, "submit_failure.html")
        return False

    def _focus_search_box_state(self, page: Page, box: Locator) -> bool:
        """Click the search box to give it focus before typing (best effort)."""
        self._log_interaction_state(page, box, "before focus")
        try:
            box.click(timeout=CLICK_TIMEOUT_MS)
        except Exception as exc:
            self._log_playwright_error("Focus click failed", exc)
            return False
        self._log_interaction_state(page, box, "after focus")
        return True

    def _enter_query_state(self, page: Page, box: Locator) -> str:
        """Enter the query, falling back to the typing path when fill() is
        blocked.

        Returns "filled" when ``fill()`` put the text in the box, "typed" when
        the typing fallback was used (it also dispatches Enter), and "" when
        neither worked. The same broken interaction is never retried.
        """
        if not self._ensure_fillable(page, box):
            return self._type_query_fallback(page)
        self._log_interaction_state(page, box, "before fill")
        try:
            box.fill(self.query)
        except Exception as exc:
            self._log_playwright_error("fill() blocked", exc)
            return self._type_query_fallback(page)
        self._log_interaction_state(page, box, "after fill")
        return "filled"

    def _type_query_fallback(self, page: Page) -> str:
        """click -> Ctrl+A -> type(delay=40) -> Enter on a freshly re-resolved
        box. Returns "typed" on success, "" otherwise."""
        try:
            box = self._reacquire_search_box(page)
            self._log_interaction_state(page, box, "before typing fallback")
            box.click(timeout=CLICK_TIMEOUT_MS)
            box.press("Control+A")
            box.type(self.query, delay=40)
            box.press("Enter")
            self._log_interaction_state(page, box, "after typing fallback")
            return "typed"
        except Exception as exc:
            self._log_playwright_error("Typing fallback failed", exc)
            return ""

    def _submit_query_state(self, page: Page) -> bool:
        """Dispatch Enter via the most robust available channel."""
        if self._press_enter_via_keyboard(page):
            return True
        try:
            box = self._reacquire_search_box(page)
        except ProviderElementNotFoundError:
            return False
        try:
            box.press("Enter")
            return True
        except Exception as exc:
            self._logger.debug("box.press(Enter) failed: %s", repr(exc))
        if self._submit_form_via_js(page):
            return True
        return self._click_search_button(page)

    def _press_enter_via_keyboard(self, page: Page) -> bool:
        try:
            page.keyboard.press("Enter")
            return True
        except Exception:
            return False

    def _submit_form_via_js(self, page: Page) -> bool:
        try:
            page.locator("form").first.evaluate(
                "form => form.requestSubmit ? form.requestSubmit() : form.submit()"
            )
            return True
        except Exception:
            return False

    def _click_search_button(self, page: Page) -> bool:
        for selector in SEARCH_BUTTON_SELECTORS:
            try:
                locator = page.locator(selector).first
                if locator.count() == 0:
                    continue
                locator.click(timeout=CLICK_TIMEOUT_MS)
                return True
            except Exception:
                continue
        return False

    def _wait_for_submission(self, page: Page) -> None:
        """Wait for the Enter press to take effect without fixed sleeps.

        The wait ends as soon as ONE of the following holds: the URL moved to
        the results route, a results feed rendered, the search box reports the
        query as its value, or the network went idle. ``wait_for_function``
        evaluates the DOM predicate event-driven; the polling loop only runs in
        environments without ``wait_for_function`` (test doubles) or after that
        wait timed out.
        """
        self._enter_state("WaitForResults")
        self._logger.info("Waiting for the submission to land...")
        if self._submission_landed(page):
            return
        try:
            page.wait_for_function(
                SUBMISSION_LANDED_JS, arg=self.query, timeout=self._settings.timeout
            )
            return
        except Exception as exc:
            self._logger.debug("wait_for_function unavailable/failed: %s", repr(exc))
        try:
            page.wait_for_load_state("networkidle", timeout=2_000)
            if self._submission_landed(page):
                return
        except Exception as exc:
            self._logger.debug("networkidle wait failed: %s", repr(exc))
        for _ in range(20):
            if self._submission_landed(page):
                return
            page.wait_for_timeout(250)
        self._logger.warning("Submission-landing wait timed out; continuing to the results check.")

    def _submission_landed(self, page: Page) -> bool:
        """True when any submission outcome is already observable."""
        if self._results_visible(page):
            return True
        for _description, locator in self._search_strategies(page):
            try:
                if locator.first.input_value(timeout=500) == self.query:
                    return True
            except Exception:
                continue
        return False

    # ------------------------------------------------------------------ #
    # Results
    # ------------------------------------------------------------------ #

    def _wait_for_results(self, page: Page) -> None:
        """Wait for a results container to render, retrying each selector."""
        self._logger.info("Waiting for results...")
        per_selector_timeout = max(self._settings.timeout // len(RESULTS_CONTAINER_SELECTORS), 500)
        for attempt in range(1, RESULTS_ATTEMPTS + 1):
            if self._results_visible(page):
                self._logger.info("Results loaded successfully.")
                self._save_screenshot(page, "results.png")
                self._save_html(page, "results.html")
                return
            for selector in RESULTS_CONTAINER_SELECTORS:
                self._logger.info("Trying results selector: %s", selector)
                try:
                    page.locator(selector).first.wait_for(timeout=per_selector_timeout)
                    self._logger.debug("Results container '%s' matched.", selector)
                    self._logger.info("Results loaded successfully.")
                    self._save_screenshot(page, "results.png")
                    self._save_html(page, "results.html")
                    return
                except Exception as exc:
                    self._logger.debug("Results selector '%s' failed: %s", selector, exc)
            self._logger.warning("Results not visible (attempt %d/%d).", attempt, RESULTS_ATTEMPTS)
            page.wait_for_timeout(RETRY_DELAY_MS)
        self._capture_diagnostics(page, "results")
        self._write_diagnostic_report(page, f"results never loaded for '{self.query}'")
        raise ProviderSearchError(f"Search results did not load for '{self.query}'.")

    def _results_visible(self, page: Page) -> bool:
        """Best-effort check that a results container is on screen."""
        try:
            if "maps/search/" in (page.url or ""):
                return True
        except Exception:
            pass
        for selector in RESULTS_CONTAINER_SELECTORS:
            try:
                locator = page.locator(selector).first
                if locator.count() > 0 and self._locator_check(locator, "is_visible") is True:
                    return True
            except Exception:
                continue
        return False

    # ------------------------------------------------------------------ #
    # Collection / extraction / export
    # ------------------------------------------------------------------ #

    def _collect_businesses(self, page: Page) -> None:
        """Discover business references by scrolling the results feed.

        The ResultCollector handles scrolling, end-of-results detection, and
        deduplication. A small candidate budget (5 default, never more than 10
        without an explicit request) is collected so the best businesses can be
        ranked before extraction. Screenshots are captured before and after the
        scroll.
        """
        self._logger.info("Collecting business references...")
        target = self._plan.max_results
        if target == DEFAULT_RESULT_LIMIT:
            self._logger.info("Default result limit: %d.", target)
        else:
            self._logger.info("Result limit: %d.", target)
        collector = ResultCollector(
            page=page,
            provider_name=self.name,
            max_results=candidate_budget(target),
            logger=self._logger,
        )
        self._save_screenshot(page, "before_scroll.png")
        self._references = collector.collect()
        self._save_screenshot(page, "after_scroll.png")
        self._logger.info("Total %d business references.", len(self._references))

    def _rank_and_select(self) -> None:
        """Rank the collected candidates and keep only the best few.

        Only the top businesses (by card signals and result position) are kept;
        extraction then visits exactly those pages, so a default search opens
        five pages instead of the whole pool.
        """
        if not self._references:
            return
        target = self._plan.max_results
        self._logger.info("Ranking businesses...")
        selected = select_top(self._references, target)
        self._references = selected
        self._logger.info("Selected top %d businesses.", len(selected))

    def _extract_business(self, page: Page) -> None:
        """Open every business and extract a structured Lead.

        A failure to open or extract one business is logged, captured as
        extraction_failure.png, and skipped; the remaining businesses are
        always processed.
        """
        navigator = self._navigator or BusinessNavigator(
            settings=self._settings, logger=self._logger
        )
        extractor = self._extractor or BusinessDetailExtractor(logger=self._logger)
        self._logger.info("Beginning extraction...")
        self._logger.info("%d businesses discovered.", len(self._references))
        self._leads = []
        self._details = []
        for index, reference in enumerate(self._references, start=1):
            self._logger.info("Opening Business %d.", index)
            try:
                business_page = navigator.open(reference, page)
                lead = extractor.extract(business_page, reference, search_query=self.query)
                extra = self._extract_supplemental(business_page)
            except Exception as exc:
                self._logger.warning(
                    "Failed to extract '%s': %s; skipping.",
                    reference.business_name,
                    exc,
                )
                self._save_screenshot(page, "extraction_failure.png")
                self._save_html(page, "extraction_failure.html")
                continue
            self._leads.append(lead)
            self._details.append(extra)
            self._logger.info("Business extracted successfully.")
        self._logger.info("%d businesses processed.", len(self._references))

    def _extract_supplemental(self, page: Page) -> dict[str, str]:
        """Extract rating, reviews, category, and working hours defensively."""
        extra: dict[str, str] = {}
        for field, selectors in SUPPLEMENTAL_SELECTORS.items():
            extra[field] = self._first_text_or_attribute(page, selectors)
        return extra

    def _first_text_or_attribute(self, page: Page, selectors: tuple[str, ...]) -> str:
        """Return the first readable value from a set of selectors."""
        for selector in selectors:
            locator = page.locator(selector).first
            try:
                value = locator.inner_text(timeout=SELECTOR_PROBE_TIMEOUT_MS).strip()
                if value:
                    return value
            except Exception as exc:
                self._logger.debug("Supplemental selector '%s' failed: %s", selector, exc)
            try:
                value = locator.get_attribute("aria-label", timeout=SELECTOR_PROBE_TIMEOUT_MS)
            except Exception:
                value = None
            if value:
                return value.strip()
        return ""

    def _export(self) -> None:
        """Serialize references, leads, and supplemental details to JSON."""
        self._logger.info("Exporting collected data...")
        try:
            payload = {
                "provider": self.name,
                "query": self.query,
                "references": [asdict(reference) for reference in self._references],
                "leads": [asdict(lead) for lead in self._leads],
                "details": list(self._details),
            }
            (self._debug_dir / "provider_export.json").write_text(
                json.dumps(payload, indent=2, default=str), encoding="utf-8"
            )
            self._logger.info(
                "Exported %d references and %d leads.", len(self._references), len(self._leads)
            )
        except Exception as exc:
            self._logger.warning("Export failed: %s", exc)

    # ------------------------------------------------------------------ #
    # Diagnostics
    # ------------------------------------------------------------------ #

    def _verify_active_page(self) -> None:
        """Requirement 11: make sure Playwright drives the frontmost page."""
        page = self._page
        if page is None:
            return
        try:
            page.bring_to_front()
            self._logger.info("Active page verified (brought to front). url=%s", page.url)
        except Exception as exc:
            self._logger.debug("Could not verify the active page: %s", exc)

    def _highlight(self, locator: Locator) -> None:
        """Highlight the matched element when debugging in headed mode."""
        if self._settings.headless:
            return
        try:
            locator.first.highlight()
        except Exception:
            pass

    def _capture_diagnostics(self, page: Page, stage: str) -> None:
        """Save HTML, screenshots, frames, and textbox diagnostics for a stage."""
        try:
            url = page.url
        except Exception:
            url = "?"
        try:
            title = page.title()
        except Exception:
            title = "?"
        self._logger.info("DIAGNOSTICS[%s] url=%s title=%s", stage, url, title)
        screenshot_name = "navigation.png" if stage == "navigation" else f"{stage}.png"
        html_name = "page.html" if stage == "navigation" else f"{stage}.html"
        self._save_screenshot(page, screenshot_name)
        self._save_html(page, html_name)
        frames = self._list_frames(page)
        textboxes = self._inspect_textboxes(page)
        self._write_diagnostic_section(stage, url, title, frames, textboxes)

    def _inspect_textboxes(self, page: Page) -> list[dict[str, Any]]:
        """Inspect every input/textarea: ids, labels, placeholders, classes,
        visibility, enabled/editable state, and bounding boxes."""
        boxes: list[dict[str, Any]] = []
        try:
            count = page.locator("input, textarea").count()
        except Exception:
            return boxes
        for index in range(count):
            locator = page.locator("input, textarea").nth(index)
            info = {
                "index": index,
                "id": self._attr(locator, "id"),
                "name": self._attr(locator, "name"),
                "aria-label": self._attr(locator, "aria-label"),
                "placeholder": self._attr(locator, "placeholder"),
                "role": self._attr(locator, "role"),
                "classes": self._attr(locator, "class"),
                "type": self._attr(locator, "type"),
                "visible": self._locator_check(locator, "is_visible"),
                "enabled": self._locator_check(locator, "is_enabled"),
                "editable": self._locator_check(locator, "is_editable"),
                "box": self._locator_bounding_box(locator),
            }
            boxes.append(info)
        for info in boxes:
            self._logger.info("textbox %s", json.dumps(info, default=str))
        return boxes

    def _list_frames(self, page: Page) -> list[dict[str, str]]:
        """List the main frame and every child (iframe) frame."""
        frames: list[dict[str, str]] = []
        try:
            page_frames = list(page.frames)
        except Exception:
            page_frames = [page]
        for frame in page_frames:
            url = "?"
            try:
                url = frame.url or "?"
            except Exception:
                pass
            name = getattr(frame, "name", None) or ""
            entry = {"name": name, "url": url}
            frames.append(entry)
            self._logger.info("frame %s", json.dumps(entry, default=str))
        return frames

    def _write_diagnostic_section(
        self,
        stage: str,
        url: str,
        title: str,
        frames: list[dict[str, str]],
        textboxes: list[dict[str, Any]],
    ) -> None:
        """Append a diagnostics section to the running report."""
        lines = [
            f"\n## Stage: {stage}",
            f"- url: {url}",
            f"- title: {title}",
            "- frames:",
        ]
        for frame in frames:
            lines.append(f"  - {frame.get('name', '')} -> {frame.get('url', '')}")
        lines.append("- textboxes:")
        for textbox in textboxes:
            lines.append(f"  - {json.dumps(textbox, default=str)}")
        self._append_report("\n".join(lines) + "\n")

    def _write_diagnostic_report(self, page: Page, summary: str) -> None:
        """Write a final diagnostic report explaining why the provider failed."""
        lines = [
            "# Google Maps Provider Diagnostic Report",
            f"- timestamp: {datetime.now().isoformat()}",
            f"- provider: {self.name}",
            f"- query: {self.query}",
            f"- headless: {self._settings.headless}",
            f"- slow_mo: {self._settings.slow_mo}",
            f"- summary: {summary}",
        ]
        try:
            lines.append(f"- final url: {page.url}")
        except Exception:
            pass
        try:
            lines.append(f"- final title: {page.title()}")
        except Exception:
            pass
        lines.append("")
        try:
            report = self._debug_dir / "diagnostic_report.md"
            report.write_text("\n".join(lines) + "\n", encoding="utf-8")
            self._logger.info("Diagnostic report written to %s", report)
        except Exception as exc:
            self._logger.warning("Could not write diagnostic report: %s", exc)

    def _append_report(self, text: str) -> None:
        try:
            with open(self._debug_dir / "diagnostic_report.md", "a", encoding="utf-8") as handle:
                handle.write(text)
        except Exception as exc:
            self._logger.debug("Could not append diagnostic report: %s", exc)

    # ------------------------------------------------------------------ #
    # Small defensive helpers
    # ------------------------------------------------------------------ #

    def _locator_count(self, locator: Locator) -> int:
        try:
            return locator.count()
        except Exception:
            return 0

    def _locator_check(self, locator: Locator, method: str) -> bool | None:
        """Return the result of a boolean locator check, or None when unknown."""
        try:
            return bool(getattr(locator, method)())
        except Exception:
            return None

    def _locator_bounding_box(self, locator: Locator) -> dict[str, float] | None:
        try:
            return locator.bounding_box()
        except Exception:
            return None

    def _log_interaction_state(self, page: Page, locator: Locator, stage: str) -> None:
        """Log the textbox's actionability, bounding box, value, and page state.

        Run before and after every interaction so a hang or stale locator is
        never silent: visible/enabled/editable, bounding box, input value, plus
        the current URL and title.
        """
        state: dict[str, Any] = {
            "stage": stage,
            "selector": getattr(locator, "selector", None),
            "visible": self._locator_check(locator, "is_visible"),
            "enabled": self._locator_check(locator, "is_enabled"),
            "editable": self._locator_check(locator, "is_editable"),
            "box": self._locator_bounding_box(locator),
        }
        try:
            state["value"] = locator.input_value(timeout=SELECTOR_PROBE_TIMEOUT_MS)
        except Exception as exc:
            state["value"] = f"<unreadable: {exc}>"
        try:
            state["url"] = page.url
        except Exception:
            state["url"] = "?"
        try:
            state["title"] = page.title()
        except Exception:
            state["title"] = "?"
        self._logger.info("search box %s: %s", stage, json.dumps(state, default=str))

    def _log_playwright_error(self, prefix: str, exc: Exception) -> None:
        """Log the full Playwright error (message plus stack) for a failure."""
        self._logger.warning("%s: %s", prefix, repr(exc))

    def _attr(self, locator: Locator, name: str) -> str:
        try:
            value = locator.get_attribute(name)
        except Exception:
            return ""
        return value or ""

    def _is_definitely_hidden(self, locator: Locator) -> bool:
        try:
            return not locator.is_visible()
        except Exception:
            return False

    def _focus_best_effort(self, locator: Locator) -> None:
        try:
            locator.scroll_into_view_if_needed()
        except Exception:
            pass
        try:
            locator.focus()
        except Exception as exc:
            self._logger.debug("Could not focus search box candidate: %s", exc)

    def _save_screenshot(self, page: Page, filename: str) -> None:
        """Save a full-page screenshot into the debug folder."""
        try:
            page.screenshot(path=str(self._debug_dir / filename), full_page=True)
            self._logger.debug("Saved screenshot: %s", filename)
        except Exception as exc:
            self._logger.debug("Could not save screenshot '%s': %s", filename, exc)

    def _save_html(self, page: Page, filename: str) -> None:
        """Save the current page HTML into the debug folder."""
        try:
            (self._debug_dir / filename).write_text(page.content(), encoding="utf-8")
            self._logger.debug("Saved HTML: %s", filename)
        except Exception as exc:
            self._logger.debug("Could not save HTML '%s': %s", filename, exc)
