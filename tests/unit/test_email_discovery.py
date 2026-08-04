"""Tests for website navigation and email discovery.

The navigator, email validator, discovery engine, contact-page crawler, and the
pipeline enrichment are exercised against fake Playwright pages so no browser
or network is used. Email discovery must follow a fixed priority order, crawl
contact pages within bounded depth/page budgets, and a failing website must
never stop the remaining leads (Requirement 7).
"""

import logging
from pathlib import Path

import pytest

from app.config.settings import Settings
from app.exceptions import ExtractionException
from app.extractor.contact_page_crawler import ContactPageCrawler
from app.extractor.email_discovery_engine import EmailDiscoveryEngine
from app.extractor.email_validator import EmailValidator
from app.extractor.website_navigator import WebsiteNavigator
from app.models.lead import Lead
from app.models.search_plan import SearchPlan
from app.pipeline.search_pipeline import SearchPipeline
from app.providers.provider_factory import ProviderFactory
from app.providers.provider_registry import ProviderRegistry
from app.providers.search_provider import SearchProvider
from tests.fakes import FakeBrowser, FakeElement, FakePage

MAILTO_SELECTOR = 'a[href^="mailto:"]'
JSONLD_SELECTOR = 'script[type="application/ld+json"]'


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        headless=True,
        timeout=2_000,
        max_leads=50,
        search_provider="google_maps",
        browser_type="chromium",
        output_dir=tmp_path / "outputs",
        log_dir=tmp_path / "logs",
        log_level="INFO",
    )


def _lead(name: str = "Acme Corp", website: str = "https://acme.example", email: str = "") -> Lead:
    return Lead(
        business_name=name,
        phone_number="",
        email=email,
        website=website,
        location="",
        provider="google_maps",
        search_query="software companies in Karachi",
        source_url="https://www.google.com/maps/place/Acme",
    )


def _plan(provider: str = "websites") -> SearchPlan:
    return SearchPlan(
        original_prompt="software companies in Karachi",
        business_type="software companies",
        location="Karachi",
        provider=provider,
        max_results=10,
    )


class WebsitesProvider(SearchProvider):
    """A provider that hands the pipeline a fixed set of leads."""

    name = "websites"
    current_leads: list[Lead] = []

    def __init__(self, browser, plan, settings, logger=None):
        super().__init__(browser=browser, plan=plan, settings=settings, logger=logger)
        self._page = browser.new_page()
        self._leads = list(WebsitesProvider.current_leads)

    @property
    def page(self):
        return self._page

    @property
    def leads(self):
        return self._leads

    def close(self) -> None:
        pass


def _website_factory(settings: Settings, page: FakePage, leads: list[Lead]) -> ProviderFactory:
    WebsitesProvider.current_leads = leads
    registry = ProviderRegistry()
    registry.register(WebsitesProvider)
    return ProviderFactory(registry=registry, settings=settings, browser=FakeBrowser(page))


# --- EmailValidator ----------------------------------------------------------


def test_validator_normalizes_and_lowercases() -> None:
    assert EmailValidator().normalize(" Sales@Acme.Example ") == "sales@acme.example"


def test_validator_is_valid() -> None:
    validator = EmailValidator()
    assert validator.is_valid("sales@acme.example")
    assert validator.is_valid("a.b-c+d@sub.domain.co.uk")
    assert not validator.is_valid("nope")


@pytest.mark.parametrize(
    "bad",
    [
        "sales@acme",
        "sales@.com",
        "@acme.com",
        "sales @acme.com",
        "a@b@c.com",
        "sales@acme..com",
        "sales@acme.c",
        "",
    ],
)
def test_validator_rejects_malformed_emails(bad: str) -> None:
    assert EmailValidator().normalize(bad) == ""


# --- EmailDiscoveryEngine ----------------------------------------------------


def test_engine_finds_mailto_email() -> None:
    page = FakePage(
        elements={MAILTO_SELECTOR: [FakeElement(attributes={"href": "mailto:sales@acme.example"})]}
    )

    assert EmailDiscoveryEngine().discover(page) == "sales@acme.example"


def test_engine_finds_email_in_page_text() -> None:
    page = FakePage(html="Reach us at hello@acme.example or call instead.")

    assert EmailDiscoveryEngine().discover(page) == "hello@acme.example"


def test_engine_finds_email_in_footer() -> None:
    page = FakePage(elements={"footer": [FakeElement(text="Support: support@acme.example")]})

    assert EmailDiscoveryEngine().discover(page) == "support@acme.example"


def test_engine_finds_email_in_header() -> None:
    page = FakePage(elements={"header": [FakeElement(text="admin@acme.example")]})

    assert EmailDiscoveryEngine().discover(page) == "admin@acme.example"


def test_engine_finds_email_in_contact_section() -> None:
    page = FakePage(elements={"#contact": [FakeElement(text="hello@acme.example")]})

    assert EmailDiscoveryEngine().discover(page) == "hello@acme.example"


def test_engine_finds_email_in_structured_data() -> None:
    page = FakePage(
        elements={JSONLD_SELECTOR: [FakeElement(text='{"email": "json@acme.example"}')]}
    )

    assert EmailDiscoveryEngine().discover(page) == "json@acme.example"


def test_engine_prefers_mailto_over_page_text() -> None:
    page = FakePage(
        elements={MAILTO_SELECTOR: [FakeElement(attributes={"href": "mailto:sales@acme.example"})]},
        html="Also reach hello@acme.example",
    )

    assert EmailDiscoveryEngine().discover(page) == "sales@acme.example"


def test_engine_rejects_invalid_email_on_page() -> None:
    page = FakePage(html="contact notan@ and visit acme dot com")

    assert EmailDiscoveryEngine().discover(page) == ""


def test_engine_returns_empty_when_no_email() -> None:
    assert EmailDiscoveryEngine().discover(FakePage()) == ""


# --- WebsiteNavigator --------------------------------------------------------


def test_navigator_opens_website(settings: Settings) -> None:
    page = FakePage()

    result = WebsiteNavigator(settings).open(_lead(), page)

    assert result is page
    assert page.url == "https://acme.example"


def test_navigator_normalizes_missing_scheme(settings: Settings) -> None:
    assert WebsiteNavigator(settings).normalize_url("acme.example") == "https://acme.example"


def test_navigator_keeps_existing_scheme(settings: Settings) -> None:
    assert (
        WebsiteNavigator(settings).normalize_url("https://acme.example") == "https://acme.example"
    )


def test_navigator_rejects_unsupported_scheme(settings: Settings) -> None:
    assert WebsiteNavigator(settings).normalize_url("ftp://acme.example") == ""


def test_navigator_rejects_empty_url(settings: Settings) -> None:
    navigator = WebsiteNavigator(settings)
    assert navigator.normalize_url("") == ""
    assert navigator.normalize_url("   ") == ""


def test_navigator_raises_for_invalid_website(settings: Settings) -> None:
    with pytest.raises(ExtractionException):
        WebsiteNavigator(settings).open(_lead(website="ftp://acme.example"), FakePage())


def test_navigator_raises_for_empty_website(settings: Settings) -> None:
    with pytest.raises(ExtractionException):
        WebsiteNavigator(settings).open(_lead(website=""), FakePage())


def test_navigator_wraps_timeout(settings: Settings) -> None:
    page = FakePage(goto_error=TimeoutError("navigation timed out"))

    with pytest.raises(ExtractionException):
        WebsiteNavigator(settings).open(_lead(), page)


def test_navigator_wraps_broken_website(settings: Settings) -> None:
    page = FakePage(goto_errors={"https://acme.example": RuntimeError("404 Not Found")})

    with pytest.raises(ExtractionException):
        WebsiteNavigator(settings).open(_lead(), page)


# --- ContactPageCrawler ------------------------------------------------------


def test_enrich_finds_email_on_contact_page(settings: Settings) -> None:
    page = FakePage(
        elements_by_url={
            "https://acme.example": {
                "a[href]": [FakeElement(text="Contact Us", attributes={"href": "/contact"})]
            },
            "https://acme.example/contact": {
                "#contact": [FakeElement(text="Reach the team: hello@acme.example")]
            },
        }
    )

    email = ContactPageCrawler(settings).enrich(_lead(), page)

    assert email == "hello@acme.example"


def test_crawl_finds_email_on_about_page(settings: Settings) -> None:
    page = FakePage(
        elements_by_url={
            "https://acme.example": {
                "a[href]": [FakeElement(text="About Us", attributes={"href": "/about"})]
            },
            "https://acme.example/about": {
                "footer": [FakeElement(text="About Acme - sales@acme.example")]
            },
        }
    )
    page.goto("https://acme.example")

    email = ContactPageCrawler(settings).crawl(_lead(), page)

    assert email == "sales@acme.example"


def test_crawl_returns_empty_when_no_email(settings: Settings) -> None:
    page = FakePage(html="A simple homepage with no contact details.")
    page.goto("https://acme.example")

    assert ContactPageCrawler(settings).crawl(_lead(), page) == ""


def test_crawl_continues_when_contact_page_broken(settings: Settings) -> None:
    page = FakePage(
        elements_by_url={
            "https://acme.example": {
                "a[href]": [FakeElement(text="Contact", attributes={"href": "/contact"})]
            }
        },
        goto_errors={"https://acme.example/contact": RuntimeError("connection reset")},
    )
    page.goto("https://acme.example")

    assert ContactPageCrawler(settings).crawl(_lead(), page) == ""


def test_crawl_respects_max_depth(settings: Settings) -> None:
    page = FakePage(
        elements_by_url={
            "https://acme.example": {
                "a[href]": [FakeElement(text="Contact", attributes={"href": "/level1"})]
            },
            "https://acme.example/level1": {
                "a[href]": [FakeElement(text="Contact", attributes={"href": "/level2"})]
            },
            "https://acme.example/level2": {
                "a[href]": [FakeElement(text="Contact", attributes={"href": "/level3"})]
            },
            "https://acme.example/level3": {"#contact": [FakeElement(text="deep@acme.example")]},
        }
    )
    page.goto("https://acme.example")

    email = ContactPageCrawler(settings).crawl(_lead(), page)

    assert email == ""
    gotos = [entry for entry in page.waited_for if entry.startswith("goto:")]
    assert gotos == [
        "goto:https://acme.example",
        "goto:https://acme.example/level1",
        "goto:https://acme.example/level2",
    ]


def test_crawl_limits_pages_per_website(settings: Settings) -> None:
    elements_by_url = {
        "https://acme.example": {
            "a[href]": [
                FakeElement(text="Contact", attributes={"href": f"/page{i}"}) for i in range(8)
            ]
        }
    }
    for i in range(8):
        elements_by_url[f"https://acme.example/page{i}"] = {
            "footer": [FakeElement(text=f"no-email-{i}")]
        }
    page = FakePage(elements_by_url=elements_by_url)
    page.goto("https://acme.example")

    email = ContactPageCrawler(settings).crawl(_lead(), page)

    assert email == ""
    gotos = [entry for entry in page.waited_for if entry.startswith("goto:")]
    assert len(gotos) == 5
    assert gotos[0] == "goto:https://acme.example"


class RedirectingPage(FakePage):
    def goto(self, url: str, wait_until: str = "load", timeout: int | None = None) -> None:
        super().goto("https://www.acme.example", wait_until=wait_until, timeout=timeout)


def test_navigator_follows_redirect_to_final_page(settings: Settings) -> None:
    page = RedirectingPage(
        content_by_url={"https://www.acme.example": "Redirected site - sales@acme.example"}
    )

    email = ContactPageCrawler(settings).enrich(_lead(website="https://acme.example"), page)

    assert email == "sales@acme.example"
    assert page.url == "https://www.acme.example"


# --- SearchPipeline enrichment -----------------------------------------------


def test_pipeline_enriches_lead_with_website_email(settings: Settings) -> None:
    page = FakePage(
        elements_by_url={
            "https://acme.example": {
                MAILTO_SELECTOR: [FakeElement(attributes={"href": "mailto:sales@acme.example"})]
            }
        }
    )
    factory = _website_factory(settings, page, [_lead()])

    result = SearchPipeline(factory=factory).run(_plan())

    assert result.success is True
    assert result.lead_count == 1
    assert result.leads[0].email == "sales@acme.example"


def test_pipeline_preserves_existing_email(settings: Settings) -> None:
    page = FakePage(
        elements_by_url={
            "https://acme.example": {
                MAILTO_SELECTOR: [FakeElement(attributes={"href": "mailto:other@acme.example"})]
            }
        }
    )
    factory = _website_factory(settings, page, [_lead(email="existing@acme.example")])

    result = SearchPipeline(factory=factory).run(_plan())

    assert result.leads[0].email == "existing@acme.example"


def test_pipeline_skips_leads_without_website(settings: Settings) -> None:
    page = FakePage(html="unused")
    lead = _lead(website="")
    factory = _website_factory(settings, page, [lead])

    result = SearchPipeline(factory=factory).run(_plan())

    assert result.leads[0].website == ""
    assert result.leads[0].email == ""


def test_pipeline_enriches_fifty_websites(settings: Settings) -> None:
    elements_by_url: dict[str, dict[str, list[FakeElement]]] = {}
    leads: list[Lead] = []
    for i in range(50):
        url = f"https://site{i}.example"
        elements_by_url[url] = {
            MAILTO_SELECTOR: [FakeElement(attributes={"href": f"mailto:info{i}@site{i}.example"})]
        }
        leads.append(_lead(name=f"Site {i}", website=url))
    page = FakePage(elements_by_url=elements_by_url)
    factory = _website_factory(settings, page, leads)

    result = SearchPipeline(factory=factory).run(_plan())

    assert result.lead_count == 50
    for i, lead in enumerate(result.leads):
        assert lead.email == f"info{i}@site{i}.example"


def test_pipeline_continues_after_website_failures(settings: Settings) -> None:
    page = FakePage(
        elements_by_url={
            "https://good1.example": {
                MAILTO_SELECTOR: [FakeElement(attributes={"href": "mailto:one@good1.example"})]
            },
            "https://good2.example": {
                MAILTO_SELECTOR: [FakeElement(attributes={"href": "mailto:two@good2.example"})]
            },
        },
        goto_errors={"https://broken.example": RuntimeError("connection refused")},
    )
    factory = _website_factory(
        settings,
        page,
        [
            _lead(name="Good 1", website="https://good1.example"),
            _lead(name="Broken", website="https://broken.example"),
            _lead(name="Good 2", website="https://good2.example"),
        ],
    )

    result = SearchPipeline(factory=factory).run(_plan())

    assert result.success is True
    assert result.leads[0].email == "one@good1.example"
    assert result.leads[1].email == ""
    assert result.leads[2].email == "two@good2.example"


def test_pipeline_survives_website_timeout(settings: Settings) -> None:
    page = FakePage(goto_error=TimeoutError("navigation timed out"))
    factory = _website_factory(settings, page, [_lead()])

    result = SearchPipeline(factory=factory).run(_plan())

    assert result.success is True
    assert result.leads[0].email == ""


def test_pipeline_logs_email_discovery(
    caplog: pytest.LogCaptureFixture, settings: Settings
) -> None:
    page = FakePage(
        elements_by_url={
            "https://acme.example": {
                MAILTO_SELECTOR: [FakeElement(attributes={"href": "mailto:sales@acme.example"})]
            }
        }
    )
    factory = _website_factory(settings, page, [_lead()])

    with caplog.at_level(logging.INFO):
        SearchPipeline(factory=factory).run(_plan())

    messages = [record.message for record in caplog.records]
    assert any("Opening website https://acme.example." in message for message in messages)
    assert any("Homepage scanned" in message for message in messages)
    assert any(
        "Email discovered for 'Acme Corp': sales@acme.example." in message for message in messages
    )
