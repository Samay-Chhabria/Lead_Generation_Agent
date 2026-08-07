"""Shared fake Playwright browser/page/locator implementations.

The fakes let provider, collector, and extraction tests run without a real
browser. A FakePage simulates a results feed: it holds a list of FakeElement
cards and a scroll callback that can append more cards on each scroll, so
lazy-loading behaviour can be exercised deterministically. Locators for
selectors listed in `card_selectors` enumerate the page's cards; selectors
listed in `elements` return those exact elements; every other present selector
matches a single generic element. Elements and page content can also be
provided per navigated URL (`elements_by_url`, `content_by_url`) so a
website-scraping run can serve different pages. Navigation can be made to fail
globally (`goto_error`) or per URL (`goto_errors`).
"""

from collections.abc import Callable
from typing import Any

from app.models.lead import Lead
from app.providers.provider_factory import ProviderFactory
from app.providers.provider_registry import ProviderRegistry
from app.providers.search_provider import SearchProvider


class FakeElement:
    """A single fake DOM element with attributes and text."""

    def __init__(self, attributes: dict[str, str] | None = None, text: str = "") -> None:
        self.attributes = dict(attributes or {})
        self.text = text

    def get_attribute(self, name: str, timeout: float | None = None) -> str | None:
        return self.attributes.get(name)

    def inner_text(self, timeout: float | None = None) -> str:
        return self.text


def fake_card(name: str, url: str, entity_id: str | None = None) -> FakeElement:
    """Build a business-card element with the common Google Maps attributes."""
    attributes: dict[str, str] = {"aria-label": name, "href": url}
    if entity_id is not None:
        attributes["data-entity-id"] = entity_id
    return FakeElement(attributes=attributes)


class FakeKeyboard:
    """A minimal Playwright Keyboard stand-in that records pressed keys."""

    def __init__(self, page: "FakePage") -> None:
        self._page = page

    def press(self, key: str) -> None:
        self._page.pressed_keys.append(key)


class FakeLocator:
    """A Playwright Locator stand-in bound to a page and optional card index."""

    def __init__(self, page: "FakePage", selector: str, index: int | None = None) -> None:
        self._page = page
        self.selector = selector
        self._index = index

    def _matched(self) -> list[FakeElement]:
        if self.selector in self._page.missing:
            return []
        if self._page.url in self._page.elements_by_url:
            url_elements = self._page.elements_by_url[self._page.url]
            if self.selector in url_elements:
                return url_elements[self.selector]
        if self.selector in self._page.card_selectors:
            return self._page.cards
        if self.selector in self._page.elements:
            return self._page.elements[self.selector]
        if self.selector in self._page.semantic:
            return [FakeElement()]
        if self.selector.startswith(("role=", "label=", "placeholder=")):
            return []
        return [FakeElement()]

    def count(self) -> int:
        return len(self._matched())

    def all(self) -> list["FakeLocator"]:
        matched = self._matched()
        return [FakeLocator(self._page, self.selector, index=i) for i in range(len(matched))]

    @property
    def first(self) -> "FakeLocator":
        return FakeLocator(self._page, self.selector, index=0)

    def nth(self, index: int) -> "FakeLocator":
        return FakeLocator(self._page, self.selector, index=index)

    def wait_for(self, timeout: int | None = None) -> None:
        if self.selector in self._page.missing:
            raise TimeoutError(f"Timeout waiting for selector '{self.selector}'.")
        if not self._matched():
            raise TimeoutError(f"Timeout waiting for selector '{self.selector}'.")
        if self._index is not None and self._index >= len(self._matched()):
            raise TimeoutError(
                f"Timeout waiting for selector '{self.selector}' at index {self._index}."
            )
        if self.selector in self._page.hidden:
            raise TimeoutError(f"Timeout waiting for hidden selector '{self.selector}'.")
        self._page.waited_for.append(self.selector)

    def click(self, timeout: int | None = None) -> None:
        self._check_present()
        if self.selector in self._page.hidden:
            raise TimeoutError(f"Element '{self.selector}' is hidden.")
        self._page.clicks.append(self.selector)

    def fill(self, value: str) -> None:
        self._check_present()
        self._page.fills.append((self.selector, value))
        if self.selector in self._page.fill_errors:
            raise TimeoutError(f"Cannot fill element '{self.selector}'.")
        self._page.values[self.selector] = value

    def type(self, text: str, delay: float | None = None) -> None:
        self._check_present()
        self._page.typed.append((self.selector, text, delay))
        self._page.values[self.selector] = text

    def input_value(self, timeout: float | None = None) -> str:
        self._check_present()
        return self._page.values.get(self.selector, "")

    def press(self, key: str) -> None:
        self._check_present()
        self._page.presses.append((self.selector, key))

    def evaluate(self, expression: str, arg: Any = None) -> Any:
        self._check_present()
        self._page.evaluations.append((self.selector, expression, arg))
        if "scroll" in expression:
            return self._page._handle_scroll()
        return None

    def get_attribute(self, name: str, timeout: float | None = None) -> str | None:
        return self._checked_element().get_attribute(name)

    def inner_text(self, timeout: float | None = None) -> str:
        return self._checked_element().inner_text()

    def is_visible(self) -> bool:
        if self.selector in self._page.hidden:
            return False
        return self._present()

    def is_enabled(self) -> bool:
        if self.selector in self._page.disabled:
            return False
        return self._present()

    def is_editable(self) -> bool:
        if self.selector in self._page.not_editable:
            return False
        return self._present()

    def bounding_box(self) -> dict[str, float] | None:
        if not self._present():
            return None
        return {"x": 0.0, "y": 0.0, "width": 100.0, "height": 24.0}

    def scroll_into_view_if_needed(self) -> None:
        self._check_present()

    def focus(self) -> None:
        self._check_present()

    def highlight(self) -> None:
        self._check_present()

    def _present(self) -> bool:
        return not self.selector.startswith(("role=", "label=", "placeholder=")) and bool(
            self._matched()
        )

    def _checked_element(self) -> FakeElement:
        if self.selector in self._page.missing:
            raise TimeoutError(f"Element '{self.selector}' not found.")
        matched = self._matched()
        index = 0 if self._index is None else self._index
        if not matched or index >= len(matched):
            raise TimeoutError(f"Element '{self.selector}' at index {index} not found.")
        return matched[index]

    def _check_present(self) -> None:
        if self.selector in self._page.missing:
            raise TimeoutError(f"Element '{self.selector}' not found.")
        if not self._matched():
            raise TimeoutError(f"Element '{self.selector}' not found.")


class FakePage:
    """A minimal Playwright Page stand-in with a simulated results feed."""

    def __init__(
        self,
        missing: set[str] | None = None,
        goto_error: Exception | None = None,
        cards: list[FakeElement] | None = None,
        card_selectors: set[str] | None = None,
        scroll_callback: Callable[["FakePage"], None] | None = None,
        elements: dict[str, list[FakeElement]] | None = None,
        goto_errors: dict[str, Exception] | None = None,
        elements_by_url: dict[str, dict[str, list[FakeElement]]] | None = None,
        html: str = "",
        content_by_url: dict[str, str] | None = None,
        hidden: set[str] | None = None,
        disabled: set[str] | None = None,
        not_editable: set[str] | None = None,
        fill_errors: set[str] | None = None,
    ) -> None:
        self.missing = set(missing or ())
        self.hidden = set(hidden or ())
        self.disabled = set(disabled or ())
        self.not_editable = set(not_editable or ())
        self.fill_errors = set(fill_errors or ())
        self.semantic: set[str] = set()
        self.goto_error = goto_error
        self.goto_errors = dict(goto_errors or {})
        self.cards = list(cards or [])
        self.card_selectors = set(card_selectors or ())
        self.elements = dict(elements or {})
        self.elements_by_url = dict(elements_by_url or {})
        self.html = html
        self.content_by_url = dict(content_by_url or {})
        self.scroll_callback = scroll_callback
        self.waited_for: list[str] = []
        self.fills: list[tuple[str, str]] = []
        self.presses: list[tuple[str, str]] = []
        self.typed: list[tuple[str, str, float | None]] = []
        self.values: dict[str, str] = {}
        self.pressed_keys: list[str] = []
        self.evaluations: list[tuple[str, str, Any]] = []
        self.clicks: list[str] = []
        self.screenshots: list[str] = []
        self.load_states: list[str] = []
        self.title_value: str = "Google Maps"
        self.default_timeout: int | None = None
        self.url: str | None = None
        self.visited_url: str | None = None
        self.scroll_count = 0
        self._closed = False
        self.keyboard = FakeKeyboard(self)

    def set_default_timeout(self, timeout: int) -> None:
        self.default_timeout = timeout

    def title(self) -> str:
        return self.title_value

    def wait_for_timeout(self, milliseconds: int) -> None:
        pass

    def wait_for_load_state(self, state: str = "load", timeout: int | None = None) -> None:
        self.load_states.append(state)

    def screenshot(self, path: str, full_page: bool = False) -> None:
        self.screenshots.append(path)

    def get_by_label(self, label: str) -> FakeLocator:
        return FakeLocator(self, f'label="{label}"')

    def get_by_placeholder(self, text: str) -> FakeLocator:
        return FakeLocator(self, f'placeholder="{text}"')

    def get_by_role(self, role: str, name: str | None = None, exact: bool = False) -> FakeLocator:
        if name:
            return FakeLocator(self, f'role={role}:name="{name}"')
        return FakeLocator(self, f"role={role}")

    def goto(self, url: str, wait_until: str = "load", timeout: int | None = None) -> None:
        if url in self.goto_errors:
            raise self.goto_errors[url]
        if self.goto_error is not None:
            raise self.goto_error
        self.visited_url = url
        self.url = url
        self.waited_for.append(f"goto:{url}")

    def content(self) -> str:
        if self.url in self.content_by_url:
            return self.content_by_url[self.url]
        return self.html

    def locator(self, selector: str) -> FakeLocator:
        return FakeLocator(self, selector)

    def _handle_scroll(self) -> None:
        self.scroll_count += 1
        if self.scroll_callback is not None:
            self.scroll_callback(self)

    def is_closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        self._closed = True


class FakeBrowser:
    """A minimal BrowserManager stand-in that hands out a FakePage."""

    def __init__(self, page: FakePage | None = None) -> None:
        self._page = page or FakePage()
        self._running = False
        self.launch_count = 0
        self.close_count = 0

    @property
    def page(self) -> FakePage:
        return self._page

    def is_running(self) -> bool:
        return self._running

    def launch(self) -> FakePage:
        self.launch_count += 1
        self._running = True
        return self._page

    def new_page(self) -> FakePage:
        self._running = True
        return self._page

    def close(self) -> None:
        self.close_count += 1
        self._running = False


class FixedLeadsProvider(SearchProvider):
    """A provider that hands the pipeline a fixed set of leads.

    Set ``current_leads`` (a class attribute) to the leads the next run should
    hand out. It never touches the network and closes without side effects, so
    full end-to-end runs can be exercised deterministically in tests.
    """

    name = "fixed"
    current_leads: list[Lead] = []

    def __init__(self, browser, plan, settings, logger=None) -> None:
        super().__init__(browser=browser, plan=plan, settings=settings, logger=logger)
        self._page = browser.new_page()
        self._leads = list(FixedLeadsProvider.current_leads)

    @property
    def page(self) -> FakePage:
        return self._page

    @property
    def leads(self) -> list[Lead]:
        return self._leads

    def close(self) -> None:
        pass


def build_fixed_factory(
    settings: Any,
    browser: FakeBrowser,
    leads: list[Lead],
) -> ProviderFactory:
    """Build a ProviderFactory serving ``leads`` through the 'fixed' provider."""
    FixedLeadsProvider.current_leads = list(leads)
    registry = ProviderRegistry()
    registry.register(FixedLeadsProvider)
    return ProviderFactory(registry=registry, settings=settings, browser=browser)
