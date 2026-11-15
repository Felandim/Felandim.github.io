import json
from unittest.mock import Mock

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from serie_b_2026.main import (
    EXPECTED_MATCHES,
    GAME_SELECTOR,
    ROUND_LABEL,
    SOURCE_URL,
    load_completed_matches,
    load_source_page,
)


def final_matches():
    return [
        {
            "round": number,
            "home": f"Mandante {number}-{game}",
            "away": f"Visitante {number}-{game}",
            "score": "1 x 0",
        }
        for number in range(1, 39)
        for game in range(1, 11)
    ]


def test_load_completed_matches_reuses_the_valid_final_table(tmp_path):
    path = tmp_path / "serie-b.json"
    path.write_text(json.dumps({"matches": final_matches()}), encoding="utf-8")

    matches = load_completed_matches(str(path))

    assert matches is not None
    assert len(matches) == EXPECTED_MATCHES


def test_load_completed_matches_rejects_an_unfinished_table(tmp_path):
    matches = final_matches()
    matches[-1]["score"] = "-"
    path = tmp_path / "serie-b.json"
    path.write_text(json.dumps({"matches": matches}), encoding="utf-8")

    assert load_completed_matches(str(path)) is None


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
