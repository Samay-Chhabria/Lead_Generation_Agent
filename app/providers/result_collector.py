"""Business result discovery.

ResultCollector turns a rendered search results page into a list of
BusinessReference objects. It locates business cards on the page, scrolls the
results feed to reveal newly loaded listings, deduplicates them, and stops when
the requested maximum is reached or when no new businesses appear after several
consecutive scrolls. Discovery only: no contact data (phone, email, website,
address) is extracted here.
"""

import logging

from playwright.sync_api import Page

from app.config.logging_config import get_logger
from app.models.business_reference import BusinessReference

BUSINESS_CARD_SELECTORS = (
    'div[role="feed"] a[href^="https://www.google.com/maps/place/"]',
    'div[role="feed"] [data-entity-id]',
)
SCROLL_CONTAINER_SELECTOR = 'div[role="feed"]'
MAX_STALLED_SCROLLS = 5
SETTLE_TIMEOUT = 2_000


class ResultCollector:
    """Discover business listings on a rendered search results page.

    Args:
        page: The Playwright page containing the results feed.
        provider_name: The name of the provider that produced the page; stored
            on every collected reference.
        max_results: Stop collecting once this many unique references are
            found.
        logger: Optional logger; a package logger is used when omitted.
    """

    def __init__(
        self,
        page: Page,
        provider_name: str,
        max_results: int,
        logger: logging.Logger | None = None,
    ) -> None:
        self._page = page
        self._provider_name = provider_name
        self._max_results = max_results
        self._logger = logger or get_logger("collector")

    def collect(self) -> list[BusinessReference]:
        """Scroll the results feed and collect unique business references.

        Returns:
            The deduplicated references, in discovery order.

        The collector stops when max_results unique references are collected,
        or when MAX_STALLED_SCROLLS consecutive scrolls produce no new
        references. Scrolling and element-wait failures are logged and treated
        as stalled scrolls so the collector always terminates.
        """
        self._logger.info("Collecting business references...")
        references: list[BusinessReference] = []
        seen: set[str] = set()
        self._logger.info("Scrolling started.")
        self._absorb(references, seen)

        stalled_scrolls = 0
        while len(references) < self._max_results:
            self._scroll()
            self._wait_for_new_cards(len(references))
            discovered = self._absorb(references, seen)
            if len(references) >= self._max_results:
                break
            if discovered == 0:
                stalled_scrolls += 1
                self._logger.info("Scroll %d found no new businesses.", stalled_scrolls)
                if stalled_scrolls >= MAX_STALLED_SCROLLS:
                    self._logger.info("No more results.")
                    break
            else:
                stalled_scrolls = 0
        self._logger.info("Scrolling completed.")

        if len(references) >= self._max_results:
            self._logger.info("Maximum reached (%d businesses).", len(references))
        elif not references:
            self._logger.info("No business references found.")
        self._logger.info("Business references collected (total %d).", len(references))
        return references

    def _absorb(
        self,
        references: list[BusinessReference],
        seen: set[str],
    ) -> int:
        """Add newly visible references, returning how many were new.

        Collection stops early once the maximum is reached even when more
        cards are still visible on the page.
        """
        discovered = 0
        skipped = 0
        for candidate in self._read_cards():
            if len(references) >= self._max_results:
                break
            key = candidate.dedupe_key
            if key in seen:
                skipped += 1
                continue
            seen.add(key)
            references.append(candidate)
            discovered += 1
            self._logger.debug(
                "Discovered business %d: %s (%s).",
                candidate.listing_index,
                candidate.business_name,
                key,
            )
        if skipped:
            self._logger.info("Duplicates skipped: %d.", skipped)
        return discovered

    def _read_cards(self) -> list[BusinessReference]:
        """Read the currently visible cards into fresh references.

        Cards are read in DOM order across every configured card selector, so
        the listing_index reflects each card's position among the visible
        matches. Cards without a readable name are skipped.
        """
        references: list[BusinessReference] = []
        index = 0
        for selector in BUSINESS_CARD_SELECTORS:
            try:
                elements = self._page.locator(selector).all()
            except Exception as exc:
                self._logger.debug("Card selector '%s' failed: %s", selector, exc)
                continue
            for element in elements:
                reference = self._build_reference(element, index)
                if reference is not None:
                    references.append(reference)
                    index += 1
        return references

    def _build_reference(self, element, index: int) -> BusinessReference | None:
        """Build a reference from a single card element, or None when the
        card has no readable name."""
        try:
            name = (element.get_attribute("aria-label") or element.inner_text()).strip()
            url = (element.get_attribute("href") or "").strip()
            entity_id = (element.get_attribute("data-entity-id") or "").strip()
        except Exception as exc:
            self._logger.debug("Could not read card element: %s", exc)
            return None
        if not name:
            return None
        business_id = entity_id or url or name
        return BusinessReference(
            business_id=business_id,
            business_name=name,
            listing_url=url or None,
            listing_index=index,
            provider=self._provider_name,
        )

    def _scroll(self) -> None:
        """Scroll the results feed to its bottom."""
        try:
            self._page.locator(SCROLL_CONTAINER_SELECTOR).evaluate(
                "el => el.scrollTo(0, el.scrollHeight)"
            )
        except Exception as exc:
            self._logger.warning("Failed to scroll results feed: %s", exc)

    def _wait_for_new_cards(self, index: int) -> None:
        """Wait up to SETTLE_TIMEOUT for the card at the given index.

        Index equals the number of collected references, so this waits for a
        card that does not exist yet and succeeds as soon as lazy-loaded
        content adds it. Timeouts are expected when scrolling reaches the end
        of the results and are swallowed; the stalled-scroll counter governs
        termination.
        """
        try:
            self._page.locator(BUSINESS_CARD_SELECTORS[0]).nth(index).wait_for(
                timeout=SETTLE_TIMEOUT
            )
        except Exception as exc:
            self._logger.debug("No new card appeared yet: %s", exc)
