"""The report's in-page filters must agree with the pipeline.

The page re-aggregates pre-computed facts in the browser, so these drive the real
controls in a real browser and compare what is on screen with figures worked out
independently of the pipeline: ``tools/profile_selections.py`` re-derives them from the
raw CSVs, applying the cleaning rules as ``docs/data-quality.md`` states them in prose.
Run it to regenerate every expected value below.
"""

from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page, sync_playwright

from retail_analytics.config import Settings
from retail_analytics.pipeline import run_pipeline

DATA_DIR = Path(__file__).parents[1] / "data"

# Independent expected values, printed by tools/profile_selections.py.
# Turnover is (store name, ratio) in the order the report ranks them.
SELECTIONS = {
    "the whole month": {
        "margin": "10,301,980",
        "stores": [],
        "from": "2024-03-01",
        "to": "2024-03-31",
        "revenue": "57,423,657",
        "margin_pct": "17.9%",
        "units": "53,846",
        "lines": "28,060",
        "returns": "1,179,763",
        "turnover": [
            ("Izmir Supermarket", "0.99"),
            ("Bursa Supermarket", "0.90"),
            ("Istanbul Supermarket", "0.88"),
            ("Antalya Hypermarket", "0.83"),
            ("Ankara Hypermarket", "0.82"),
        ],
    },
    "one store": {
        "margin": "1,590,395",
        "stores": ["S-001"],
        "from": "2024-03-01",
        "to": "2024-03-31",
        "revenue": "8,771,664",
        "margin_pct": "18.1%",
        "units": "8,404",
        "lines": "4,428",
        "returns": "174,841",
        "turnover": [("Istanbul Supermarket", "0.88")],
    },
    "one week": {
        "margin": "2,370,405",
        "stores": [],
        "from": "2024-03-04",
        "to": "2024-03-10",
        "revenue": "13,283,864",
        "margin_pct": "17.8%",
        "units": "12,511",
        "lines": "6,529",
        "returns": "303,274",
        "turnover": [
            ("Istanbul Supermarket", "0.25"),
            ("Antalya Hypermarket", "0.24"),
            ("Bursa Supermarket", "0.22"),
            ("Izmir Supermarket", "0.21"),
            ("Ankara Hypermarket", "0.20"),
        ],
    },
    "one store over two weeks": {
        "margin": "1,284,029",
        "stores": ["S-002"],
        "from": "2024-03-11",
        "to": "2024-03-24",
        "revenue": "6,957,461",
        "margin_pct": "18.5%",
        "units": "6,542",
        "lines": "3,378",
        "returns": "168,271",
        "turnover": [("Ankara Hypermarket", "0.41")],
    },
}


@pytest.fixture(scope="module")
def report_file(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Render the report over the real data.

    Args:
        tmp_path_factory (pytest.TempPathFactory): Pytest's module-scoped temp directory
            factory.

    Returns:
        Path: The generated ``report.html``.
    """
    out = tmp_path_factory.mktemp("report")
    run_pipeline(Settings(data_dir=DATA_DIR, output_dir=out))
    return out / "report.html"


@pytest.fixture(scope="module")
def browser() -> Iterator[Browser]:
    """Launch one headless browser for the whole module.

    Playwright's sync API allows a single driver per thread, so both the scripted and
    the unscripted page come from here.

    Yields:
        Browser: The launched browser.
    """
    with sync_playwright() as playwright:
        launched = playwright.chromium.launch()
        yield launched
        launched.close()


@pytest.fixture(scope="module")
def report_page(browser: Browser, report_file: Path) -> Page:
    """Open the rendered report in a headless browser.

    Args:
        browser (Browser): The launched browser.
        report_file (Path): The generated ``report.html``.

    Returns:
        Page: The loaded report, with a ``console_errors`` list attached.
    """
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(report_file.resolve().as_uri(), wait_until="load", timeout=120_000)
    page.wait_for_timeout(1500)
    page.console_errors = errors  # type: ignore[attr-defined]
    return page


@pytest.fixture(scope="module")
def report_page_without_scripting(browser: Browser, report_file: Path) -> Page:
    """Open the rendered report in a context with JavaScript turned off.

    Args:
        browser (Browser): The launched browser.
        report_file (Path): The generated ``report.html``.

    Returns:
        Page: The loaded report, with no script having run.
    """
    page = browser.new_context(java_script_enabled=False).new_page()
    page.goto(report_file.resolve().as_uri(), wait_until="load", timeout=120_000)
    return page


def _tick(page: Page, dropdown: str, attribute: str, values: Sequence[str]) -> None:
    """Open a multi-select dropdown and tick exactly the values given.

    Args:
        page (Page): The loaded report.
        dropdown (str): The dropdown's id, ``f-store`` or ``f-region``.
        attribute (str): The data attribute holding each option's value.
        values (Sequence[str]): The values to leave ticked.
    """
    page.click(f"#{dropdown} .multi-toggle")
    page.click(f"#{dropdown} [data-none]")
    for value in values:
        page.check(f'#{dropdown} input[{attribute}="{value}"]')
    page.click(f"#{dropdown} .multi-toggle")


def _apply(page: Page, selection: Mapping[str, object]) -> None:
    """Drive the filter controls to a selection.

    Args:
        page (Page): The loaded report.
        selection (Mapping[str, object]): One entry of ``SELECTIONS``.
    """
    page.click("#f-reset")
    stores = selection["stores"]
    if isinstance(stores, Sequence) and stores:
        _tick(page, "f-store", "data-store", stores)
    for field, value in (("#f-from", selection["from"]), ("#f-to", selection["to"])):
        page.fill(field, str(value))
        page.dispatch_event(field, "change")
    page.wait_for_timeout(300)


def _turnover_rows(page: Page) -> list[tuple[str, str]]:
    """Read the turnover table as (store name, ratio) pairs, in the order shown.

    Args:
        page (Page): The loaded report.

    Returns:
        list[tuple[str, str]]: One pair per store; empty when no week fits the range.
    """
    rows = page.eval_on_selector_all(
        "#t-turnover tbody tr",
        "rows => rows.map(r => [r.cells[0].textContent, r.cells[5].textContent])",
    )
    return [(name, ratio) for name, ratio in rows]


@pytest.mark.parametrize("name", list(SELECTIONS))
def test_filtered_figures_match_the_independent_expected_values(
    report_page: Page, name: str
) -> None:
    selection = SELECTIONS[name]
    _apply(report_page, selection)

    assert report_page.inner_text("#m-revenue").strip() == selection["revenue"]
    assert report_page.inner_text("#m-margin-pct").strip() == selection["margin_pct"]
    assert report_page.inner_text("#m-margin").strip() == selection["margin"]
    assert report_page.inner_text("#m-units").strip() == selection["units"]
    assert report_page.inner_text("#m-lines").strip() == selection["lines"]
    assert report_page.inner_text("#m-returns").strip() == selection["returns"]
    assert _turnover_rows(report_page) == selection["turnover"]


def test_choosing_a_region_leaves_only_that_regions_stores_in_play(report_page: Page) -> None:
    report_page.click("#f-reset")
    _tick(report_page, "f-region", "data-region", ["Marmara"])
    report_page.wait_for_timeout(300)

    live = report_page.eval_on_selector_all(
        "#f-store input[data-store]",
        "boxes => boxes.filter(b => b.checked && !b.disabled)"
        ".map(b => b.parentNode.textContent.trim())",
    )
    assert live == ["Istanbul Supermarket", "Bursa Supermarket"]
    assert report_page.inner_text("#f-region-summary").strip() == "Marmara"


def test_both_filters_start_showing_everything(report_page: Page) -> None:
    report_page.click("#f-reset")

    assert report_page.inner_text("#f-region-summary").strip() == "All regions"
    assert report_page.inner_text("#f-store-summary").strip() == "All stores"


def test_the_articles_tab_shows_one_ranking_measure_at_a_time(report_page: Page) -> None:
    report_page.click("#f-reset")
    report_page.click('[aria-controls="articles"]')
    visible = "sections => sections.filter(s => !s.hidden).map(s => s.dataset.measure)"

    assert report_page.eval_on_selector_all(".measure", visible) == ["revenue"]

    report_page.select_option("#f-measure", "margin_pct")
    assert report_page.eval_on_selector_all(".measure", visible) == ["margin_pct"]

    report_page.click('[aria-controls="sales"]')


def test_data_quality_totals_do_not_move_when_the_selection_changes(report_page: Page) -> None:
    report_page.click("#f-reset")
    strip_before = report_page.inner_text(".quality-strip")
    panel_before = report_page.inner_text("#quality")

    _apply(report_page, SELECTIONS["one store over two weeks"])

    assert report_page.inner_text(".quality-strip") == strip_before
    assert report_page.inner_text("#quality") == panel_before


def test_a_range_shorter_than_a_full_inventory_week_shows_the_empty_turnover_state(
    report_page: Page,
) -> None:
    _apply(report_page, {"stores": [], "from": "2024-03-05", "to": "2024-03-08"})

    assert report_page.eval_on_selector("#turnover-empty", "el => !el.hidden")
    assert report_page.eval_on_selector("#turnover-body", "el => el.hidden")


def test_the_report_loads_without_console_errors(report_page: Page) -> None:
    assert report_page.console_errors == []  # type: ignore[attr-defined]


def test_without_scripting_the_filter_bar_is_hidden(report_page_without_scripting: Page) -> None:
    assert report_page_without_scripting.is_hidden("#filters")
    assert report_page_without_scripting.is_hidden("#f-measure-field")


def test_without_scripting_the_server_rendered_figures_cover_the_whole_selection(
    report_page_without_scripting: Page,
) -> None:
    page = report_page_without_scripting
    whole = SELECTIONS["the whole month"]

    assert page.inner_text("#m-revenue").strip() == whole["revenue"]
    assert page.inner_text("#m-margin-pct").strip() == whole["margin_pct"]
    assert page.inner_text("#m-margin").strip() == whole["margin"]
    assert page.inner_text("#m-units").strip() == whole["units"]
    assert page.inner_text("#m-lines").strip() == whole["lines"]
    assert page.inner_text("#m-returns").strip() == whole["returns"]
    assert _turnover_rows(page) == whole["turnover"]


def test_the_date_controls_reach_the_end_of_the_last_inventory_week(report_page: Page) -> None:
    report_page.click("#f-reset")

    assert report_page.get_attribute("#f-to", "max") == "2024-03-31"
    assert _turnover_rows(report_page) == SELECTIONS["the whole month"]["turnover"]
