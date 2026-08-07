"""Tests for business result discovery (ResultCollector).

The collector is exercised against a fake results feed that can grow on scroll,
so lazy-loading behaviour is deterministic and no browser is launched.
"""

import logging

import pytest

from app.providers.result_collector import (
    BUSINESS_CARD_SELECTORS,
    MAX_STALLED_SCROLLS,
    SCROLL_CONTAINER_SELECTOR,
    ResultCollector,
)
from tests.fakes import FakeElement, FakePage, fake_card


def _cards(count: int, start: int = 0) -> list[FakeElement]:
    return [
        fake_card(
            f"Business {i}",
            f"https://www.google.com/maps/place/Business{i}",
            f"0x1:0x{i}",
        )
        for i in range(start, start + count)
    ]


def _collector(page: FakePage, max_results: int = 10) -> ResultCollector:
    return ResultCollector(
        page=page,
        provider_name="google_maps",
        max_results=max_results,
    )


def _feed_page(
    cards: list[FakeElement] | None = None,
    **kwargs,
) -> FakePage:
    return FakePage(
        cards=cards or [],
        card_selectors=set(BUSINESS_CARD_SELECTORS),
        **kwargs,
    )


def test_collects_ten_businesses() -> None:
    page = _feed_page(_cards(10))

    references = _collector(page, max_results=10).collect()

    assert len(references) == 10
    assert [r.business_name for r in references] == [f"Business {i}" for i in range(10)]
    assert page.scroll_count == 0


def test_collects_twenty_five_businesses() -> None:
    page = _feed_page(_cards(25))

    references = _collector(page, max_results=25).collect()

    assert len(references) == 25


def test_collects_fifty_businesses() -> None:
    page = _feed_page(_cards(50))

    references = _collector(page, max_results=50).collect()

    assert len(references) == 50


def test_stops_at_max_results() -> None:
    page = _feed_page(_cards(25))

    references = _collector(page, max_results=10).collect()

    assert len(references) == 10
    assert [r.business_name for r in references] == [f"Business {i}" for i in range(10)]
    assert page.scroll_count == 0


def test_removes_duplicate_urls() -> None:
    page = _feed_page(
        [
            fake_card("Alpha", "https://www.google.com/maps/place/Same", "0x1:0x1"),
            fake_card("Beta", "https://www.google.com/maps/place/Same", "0x1:0x2"),
            fake_card("Gamma", "https://www.google.com/maps/place/Other", "0x1:0x3"),
        ]
    )

    references = _collector(page, max_results=10).collect()

    assert [r.business_name for r in references] == ["Alpha", "Gamma"]


def test_removes_duplicate_ids_without_urls() -> None:
    page = _feed_page(
        [
            FakeElement({"aria-label": "Alpha", "data-entity-id": "0x1:0x9"}),
            FakeElement({"aria-label": "Beta", "data-entity-id": "0x1:0x9"}),
        ]
    )

    references = _collector(page, max_results=10).collect()

    assert [r.business_name for r in references] == ["Alpha"]
    assert references[0].listing_url is None
    assert references[0].business_id == "0x1:0x9"


def test_no_results_collects_nothing() -> None:
    page = _feed_page()

    references = _collector(page, max_results=10).collect()

    assert references == []
    assert page.scroll_count == MAX_STALLED_SCROLLS


def test_stops_after_stalled_scrolls_without_new_results() -> None:
    page = _feed_page(_cards(3))

    references = _collector(page, max_results=10).collect()

    assert len(references) == 3
    assert page.scroll_count == MAX_STALLED_SCROLLS


def test_dynamic_loading_scrolls_until_max() -> None:
    def grow(page: FakePage) -> None:
        page.cards.extend(_cards(min(3, 12 - len(page.cards)), start=len(page.cards)))

    page = _feed_page(_cards(3), scroll_callback=grow)

    references = _collector(page, max_results=10).collect()

    assert [r.business_name for r in references] == [f"Business {i}" for i in range(10)]
    assert page.scroll_count == 3


def test_scrolling_failure_is_graceful() -> None:
    page = _feed_page(_cards(3), missing={SCROLL_CONTAINER_SELECTOR})

    references = _collector(page, max_results=10).collect()

    assert len(references) == 3
    assert page.scroll_count == 0


def test_references_carry_provider_and_indexes() -> None:
    page = _feed_page(_cards(5))

    references = _collector(page, max_results=10).collect()

    assert all(r.provider == "google_maps" for r in references)
    assert [r.listing_index for r in references] == list(range(5))


def test_logs_collection_steps(caplog: pytest.LogCaptureFixture) -> None:
    page = _feed_page(_cards(2))

    with caplog.at_level(logging.INFO):
        _collector(page, max_results=10).collect()

    messages = [record.message for record in caplog.records]
    assert any("Collecting business references..." in message for message in messages)
    assert any("Scrolling started." in message for message in messages)
    assert any("Scrolling completed." in message for message in messages)
    assert any("No more results." in message for message in messages)
    assert any("Business references collected (total 2)." in message for message in messages)


def test_logs_duplicates_skipped(caplog: pytest.LogCaptureFixture) -> None:
    page = _feed_page(
        [
            fake_card("Alpha", "https://www.google.com/maps/place/Same", "0x1:0x1"),
            fake_card("Beta", "https://www.google.com/maps/place/Same", "0x1:0x2"),
        ]
    )

    with caplog.at_level(logging.INFO):
        references = _collector(page, max_results=10).collect()

    assert [r.business_name for r in references] == ["Alpha"]
    messages = [record.message for record in caplog.records]
    assert any(message.startswith("Duplicates skipped:") for message in messages)


def test_logs_maximum_reached(caplog: pytest.LogCaptureFixture) -> None:
    page = _feed_page(_cards(25))

    with caplog.at_level(logging.INFO):
        references = _collector(page, max_results=5).collect()

    assert len(references) == 5
    messages = [record.message for record in caplog.records]
    assert any("Maximum reached (5 businesses)." in message for message in messages)


def test_logs_stopping_search_early_when_limit_reached(
    caplog: pytest.LogCaptureFixture,
) -> None:
    page = _feed_page(_cards(25))

    with caplog.at_level(logging.INFO):
        _collector(page, max_results=5).collect()

    messages = [record.message for record in caplog.records]
    assert any("Stopping search early." in message for message in messages)


def test_reads_card_signals_from_text() -> None:
    card = FakeElement(
        {
            "aria-label": "Acme Corp",
            "href": "https://www.google.com/maps/place/Acme",
        },
        text="4.6 (210) reviews",
    )
    page = _feed_page([card])

    references = _collector(page, max_results=10).collect()

    assert references[0].business_name == "Acme Corp"
    assert references[0].rating == 4.6
    assert references[0].review_count == 210


def test_reads_card_signals_from_data_attributes() -> None:
    card = FakeElement(
        {
            "aria-label": "Acme Corp",
            "href": "https://www.google.com/maps/place/Acme",
            "data-rating": "4.7",
            "data-reviews": "320",
            "data-website": "1",
            "data-verified": "1",
        }
    )
    page = _feed_page([card])

    references = _collector(page, max_results=10).collect()

    assert references[0].rating == 4.7
    assert references[0].review_count == 320
    assert references[0].has_website is True
    assert references[0].verified is True


def test_missing_signals_are_neutral() -> None:
    page = _feed_page(_cards(2))

    references = _collector(page, max_results=10).collect()

    assert references[0].rating is None
    assert references[0].review_count is None
    assert references[0].has_website is False
    assert references[0].verified is False
