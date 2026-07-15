#!/usr/bin/env python3
"""Atualiza as 38 rodadas do Brasileirão Série A 2026 a partir do ge."""

from __future__ import annotations

import html
import json
import os
import re
from datetime import datetime
from typing import Any

from playwright.sync_api import Page, sync_playwright

SOURCE_URL = "https://ge.globo.com/futebol/brasileirao-serie-a/"
DATA_FILE = "data/serie_a_2026.json"
OUTPUT_HTML = "docs/serie_a_2026/index.html"
EXPECTED_ROUNDS = 38
MATCHES_PER_ROUND = 10
EXPECTED_MATCHES = EXPECTED_ROUNDS * MATCHES_PER_ROUND
ROUND_LABEL = ".lista-jogos__navegacao--rodada"
PREVIOUS_BUTTON = ".lista-jogos__navegacao--seta-esquerda"
NEXT_BUTTON = ".lista-jogos__navegacao--seta-direita"
GAME_SELECTOR = ".lista-jogos__jogo"
# A tabela publicada omite o status redundante exibido pelo ge.


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
        ([labelSelector, gameSelector, previousLabel, previousGame, expectedGames]) => {
          const label = document.querySelector(labelSelector)?.textContent?.trim() || '';
          const games = document.querySelectorAll(gameSelector);
          const firstGame = document.querySelector(`${gameSelector} meta[itemprop='startDate']`)
            ?.getAttribute('content') || '';
          return label !== previousLabel && games.length === expectedGames &&
                 firstGame !== '' && firstGame !== previousGame;
        }
        """,
        arg=[ROUND_LABEL, GAME_SELECTOR, old_label, old_first_game, MATCHES_PER_ROUND],
        timeout=45_000,
    )


def navigate(page: Page, selector: str) -> None:
    old_label = clean(page.locator(ROUND_LABEL).inner_text())
    first_meta = page.locator(f"{GAME_SELECTOR} meta[itemprop='startDate']").first
    old_first_game = clean(first_meta.get_attribute("content"))
    page.locator(selector).click()
    wait_for_round_change(page, old_label, old_first_game)


def scrape_visible_round(page: Page, number: int) -> list[dict[str, Any]]:
    page.wait_for_function(
        "([selector, expected]) => document.querySelectorAll(selector).length === expected",
        arg=[GAME_SELECTOR, MATCHES_PER_ROUND],
        timeout=45_000,
    )
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
                f'<tr class="group-row"><td colspan="7">{number}ª rodada</td></tr>'
            )
            current_round = number

        score = html.escape(clean(match.get("score")) or "-")
        url = clean(match.get("url"))
        if url:
            score = f'<a href="{html.escape(url, quote=True)}">{score}</a>'
        rows.append(
            "<tr data-match-row>"
            f"<td>{number}ª</td>"
            f"<td>{html.escape(clean(match.get('date')))}</td>"
            f"<td>{html.escape(clean(match.get('time')))}</td>"
            f"<td class=\"team\">{html.escape(clean(match.get('home')))}</td>"
            f"<td class=\"score\">{score}</td>"
            f"<td class=\"team\">{html.escape(clean(match.get('away')))}</td>"
            f"<td>{html.escape(clean(match.get('stadium')))}</td>"
            "</tr>"
        )

    return """<!DOCTYPE html>
<html lang="pt-br"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Jogos do Brasileirão Série A 2026: tabela completa</title>
<meta name="description" content="Consulte as 38 rodadas e os 380 jogos do Brasileirão Série A 2026, com datas, horários, placares e estádios.">
<link rel="canonical" href="https://felandim.github.io/docs/serie_a_2026/"><link rel="stylesheet" href="../../style.css"></head>
<body class="football-page"><header class="site-header"><div class="container nav-wrap"><a class="brand" href="../../index.html"><span>FL</span> Felipe Landim</a><nav class="site-nav" aria-label="Navegação principal"><a href="../../projetos.html">Projetos</a><a href="../../dados-futebol.html" aria-current="page">Dados de futebol</a><a href="../../artigos.html">Artigos</a><a href="../../about.html">Sobre</a></nav></div></header>
<main><section class="football-header"><div class="container football-intro"><div class="breadcrumb"><a href="../../index.html">Início</a><span>/</span><a href="../../dados-futebol.html">Dados de futebol</a><span>/</span><span>Série A 2026</span></div><p class="eyebrow">Atualização automática a cada 6 horas</p><h1>Brasileirão Série A 2026</h1><p>As 38 rodadas em uma tabela pesquisável.</p></div></section>
<section class="container"><div class="football-toolbar"><div class="search-field"><label for="match-search">Buscar time, estádio, data ou rodada</label><input id="match-search" type="search" placeholder="Ex.: Palmeiras, Maracanã ou 12ª" data-match-search autocomplete="off"></div><div class="result-count" data-result-count aria-live="polite"></div></div><aside class="ad-slot" data-ad-slot="football-top" hidden aria-label="Publicidade"></aside>
<div class="table-shell"><div class="table-scroll"><table class="data-table"><thead><tr><th scope="col">Rodada</th><th scope="col">Data</th><th scope="col">Hora</th><th scope="col">Mandante</th><th scope="col">Placar</th><th scope="col">Visitante</th><th scope="col">Estádio</th></tr></thead><tbody>""" + "\n".join(rows) + """</tbody></table></div><div class="source-note">Dados de origem: ge. A página é gerada automaticamente. <a href="../../dados-futebol.html">Entenda o pipeline.</a></div></div></section></main>
<footer class="site-footer"><div class="container footer-bottom"><span>© Felipe Landim</span><a href="../../dados-futebol.html">Mais dados de futebol</a></div></footer><script src="../../football.js" defer></script></body></html>\n"""


def main() -> None:
    matches = scrape_all_matches()
    data = {
        "name": "Brasileirão Série A 2026",
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
