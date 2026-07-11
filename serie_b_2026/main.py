#!/usr/bin/env python3
"""Atualiza as 38 rodadas do Brasileirão Série B 2026 a partir do ge."""

from __future__ import annotations

import html
import json
import os
import re
from datetime import datetime
from typing import Any

from playwright.sync_api import Page, sync_playwright

SOURCE_URL = "https://ge.globo.com/futebol/brasileirao-serie-b/"
DATA_FILE = "data/serie_b_2026.json"
OUTPUT_HTML = "docs/serie_b_2026/index.html"
EXPECTED_ROUNDS = 38
MATCHES_PER_ROUND = 10
EXPECTED_MATCHES = EXPECTED_ROUNDS * MATCHES_PER_ROUND
ROUND_LABEL = ".lista-jogos__navegacao--rodada"
PREVIOUS_BUTTON = ".lista-jogos__navegacao--seta-esquerda"
NEXT_BUTTON = ".lista-jogos__navegacao--seta-direita"
GAME_SELECTOR = ".lista-jogos__jogo"


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value)).strip() if value is not None else ""


def round_number(label: str) -> int:
    match = re.search(r"\d+", label)
    if not match:
        raise RuntimeError(f"Não foi possível interpretar a rodada: {label!r}")
    return int(match.group())


def wait_for_round_change(page: Page, old_label: str, old_first_game: str) -> None:
    page.wait_for_function(
        """
        ([labelSelector, gameSelector, previousLabel, previousGame]) => {
          const label = document.querySelector(labelSelector)?.textContent?.trim() || '';
          const firstGame = document.querySelector(`${gameSelector} meta[itemprop='startDate']`)
            ?.getAttribute('content') || '';
          return label !== previousLabel && firstGame !== previousGame;
        }
        """,
        arg=[ROUND_LABEL, GAME_SELECTOR, old_label, old_first_game],
        timeout=45_000,
    )


def navigate(page: Page, selector: str) -> None:
    old_label = clean(page.locator(ROUND_LABEL).inner_text())
    first_meta = page.locator(f"{GAME_SELECTOR} meta[itemprop='startDate']").first
    old_first_game = clean(first_meta.get_attribute("content"))
    page.locator(selector).click()
    wait_for_round_change(page, old_label, old_first_game)


def scrape_visible_round(page: Page, number: int) -> list[dict[str, Any]]:
    raw_matches = page.locator(GAME_SELECTOR).evaluate_all(
        """
        (nodes) => nodes.map((node) => {
          const text = (selector) => node.querySelector(selector)?.textContent?.trim() || '';
          const attribute = (selector, name) => node.querySelector(selector)?.getAttribute(name) || '';
          const homeScore = text('.placar-box__valor--mandante');
          const awayScore = text('.placar-box__valor--visitante');
          const homePenalty = text('.placar-box__penaltis-mandante');
          const awayPenalty = text('.placar-box__penaltis-visitante');
          let score = homeScore !== '' && awayScore !== '' ? `${homeScore} x ${awayScore}` : '-';
          if (homePenalty !== '' && awayPenalty !== '') {
            score += ` (pênaltis: ${homePenalty} x ${awayPenalty})`;
          }
          return {
            start: attribute("meta[itemprop='startDate']", 'content'),
            home: attribute(".placar__equipes--mandante meta[itemprop='name']", 'content') ||
                  text('.placar__equipes--mandante .equipes__nome'),
            away: attribute(".placar__equipes--visitante meta[itemprop='name']", 'content') ||
                  text('.placar__equipes--visitante .equipes__nome'),
            score,
            stadium: text('.jogo__informacoes--local'),
            status: text('.jogo__transmissao--broadcast'),
            url: attribute('a.jogo__transmissao--link', 'href')
          };
        })
        """
    )

    if len(raw_matches) != MATCHES_PER_ROUND:
        raise RuntimeError(
            f"A {number}ª rodada retornou {len(raw_matches)} partidas; "
            f"eram esperadas {MATCHES_PER_ROUND}."
        )

    matches: list[dict[str, Any]] = []
    for item in raw_matches:
        start = clean(item.get("start"))
        date = ""
        match_time = ""
        if start:
            try:
                parsed = datetime.fromisoformat(start)
                date = parsed.strftime("%d/%m/%Y")
                match_time = parsed.strftime("%H:%M")
            except ValueError:
                date = start

        home = clean(item.get("home"))
        away = clean(item.get("away"))
        if not home or not away:
            raise RuntimeError(f"Partida sem equipes na {number}ª rodada")

        matches.append(
            {
                "round": number,
                "date": date,
                "time": match_time,
                "home": home,
                "score": clean(item.get("score")) or "-",
                "away": away,
                "stadium": clean(item.get("stadium")),
                "status": clean(item.get("status")),
                "url": clean(item.get("url")),
            }
        )
    return matches


def scrape_all_matches() -> list[dict[str, Any]]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(locale="pt-BR")
        page.set_default_timeout(90_000)
        try:
            page.goto(SOURCE_URL, wait_until="domcontentloaded", timeout=120_000)
            page.wait_for_selector(ROUND_LABEL, state="visible")
            page.wait_for_selector(GAME_SELECTOR, state="attached")

            current = round_number(page.locator(ROUND_LABEL).inner_text())
            if not 1 <= current <= EXPECTED_ROUNDS:
                raise RuntimeError(f"Rodada atual inesperada: {current}")

            while current > 1:
                navigate(page, PREVIOUS_BUTTON)
                current = round_number(page.locator(ROUND_LABEL).inner_text())

            matches: list[dict[str, Any]] = []
            for expected_round in range(1, EXPECTED_ROUNDS + 1):
                current = round_number(page.locator(ROUND_LABEL).inner_text())
                if current != expected_round:
                    raise RuntimeError(
                        f"Navegação fora de sequência: esperava rodada {expected_round}, recebeu {current}."
                    )
                matches.extend(scrape_visible_round(page, current))
                print(f"Rodada {current}: {MATCHES_PER_ROUND} partidas coletadas")
                if current < EXPECTED_ROUNDS:
                    navigate(page, NEXT_BUTTON)
        finally:
            browser.close()

    if len(matches) != EXPECTED_MATCHES:
        raise RuntimeError(
            f"O ge retornou {len(matches)} partidas; eram esperadas {EXPECTED_MATCHES}."
        )
    return matches


def write_if_changed(path: str, content: str) -> bool:
    existing = None
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as file:
            existing = file.read()
    if existing == content:
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        file.write(content)
    return True


def build_html(matches: list[dict[str, Any]]) -> str:
    rows: list[str] = []
    current_round = 0
    for match in matches:
        number = int(match["round"])
        if number != current_round:
            rows.append(
                f'<tr class="round-header"><td colspan="8">{number}ª rodada</td></tr>'
            )
            current_round = number

        score = html.escape(clean(match.get("score")) or "-")
        url = clean(match.get("url"))
        if url:
            score = f'<a href="{html.escape(url, quote=True)}">{score}</a>'
        rows.append(
            "<tr>"
            f"<td>{number}ª</td>"
            f"<td>{html.escape(clean(match.get('date')))}</td>"
            f"<td>{html.escape(clean(match.get('time')))}</td>"
            f"<td class=\"team\">{html.escape(clean(match.get('home')))}</td>"
            f"<td class=\"score\">{score}</td>"
            f"<td class=\"team\">{html.escape(clean(match.get('away')))}</td>"
            f"<td>{html.escape(clean(match.get('stadium')))}</td>"
            f"<td>{html.escape(clean(match.get('status')))}</td>"
            "</tr>"
        )

    return """<!DOCTYPE html>
<html lang="pt-br"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Brasileirão Série B 2026</title>
<style>body{font-family:Arial,sans-serif;margin:20px;background:#fafafa;color:#333}h1,p{text-align:center}table{margin:auto;border-collapse:collapse;width:98%;max-width:1200px;background:white}th,td{padding:10px;border:1px solid #ddd;text-align:center}th{background:#1a1a2e;color:white}.team{text-align:left;font-weight:bold}.score{font-weight:bold}.round-header td{background:#e8e8e8;font-weight:bold;text-align:left}a{color:#007bff;text-decoration:none}</style></head>
<body><h1>Brasileirão Série B 2026</h1><p>As 38 rodadas, atualizadas automaticamente a partir do ge.</p>
<table><thead><tr><th>Rodada</th><th>Data</th><th>Hora</th><th>Mandante</th><th>Placar</th><th>Visitante</th><th>Estádio</th><th>Status</th></tr></thead><tbody>""" + "\n".join(rows) + """</tbody></table><p><a href="../index.html">← Voltar ao site</a></p></body></html>\n"""


def main() -> None:
    matches = scrape_all_matches()
    data = {
        "name": "Brasileirão Série B 2026",
        "source": SOURCE_URL,
        "rounds": EXPECTED_ROUNDS,
        "matches": matches,
    }
    json_content = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    json_changed = write_if_changed(DATA_FILE, json_content)
    html_changed = write_if_changed(OUTPUT_HTML, build_html(matches))
    print(
        f"{len(matches)} partidas armazenadas. "
        f"JSON alterado: {json_changed}. HTML alterado: {html_changed}."
    )


if __name__ == "__main__":
    main()
