from unittest.mock import Mock

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from serie_b_2026.main import GAME_SELECTOR, ROUND_LABEL, SOURCE_URL, load_source_page


def test_load_source_page_retries_a_transient_render_timeout():
    page = Mock()
    page.wait_for_selector.side_effect = [
        PlaywrightTimeoutError("rodada atrasou"),
        None,
        None,
    ]

    load_source_page(page)

    assert page.goto.call_count == 2
    page.goto.assert_called_with(SOURCE_URL, wait_until="domcontentloaded", timeout=120_000)
    assert page.wait_for_selector.call_args_list[-2].args == (ROUND_LABEL,)
    assert page.wait_for_selector.call_args_list[-1].args == (GAME_SELECTOR,)


def test_load_source_page_keeps_failure_visible_after_retry_limit():
    page = Mock()
    page.wait_for_selector.side_effect = PlaywrightTimeoutError("fonte indisponível")

    with pytest.raises(RuntimeError, match="após 2 tentativas"):
        load_source_page(page)

    assert page.goto.call_count == 2
