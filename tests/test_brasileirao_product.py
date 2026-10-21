import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


def test_scorer_coverage_and_goal_totals_match_scores():
    matches = load("serie_a_2026.json")["matches"]
    scorers = load("serie_a_2026_scorers.json")["matches"]
    completed = [match for match in matches if re.match(r"^\d+\s*x\s*\d+", match["score"])]
    assert len(scorers) >= len(completed)
    for match in completed:
        home_goals, away_goals = map(int, re.match(r"^(\d+)\s*x\s*(\d+)", match["score"]).groups())
        item = scorers[match["url"]]
        assert sum(scorer["goals"] for scorer in item["home"]) == home_goals
        assert sum(scorer["goals"] for scorer in item["away"]) == away_goals


def test_insights_cover_all_teams_and_completed_rounds():
    insights = load("brasileirao_2026_insights.json")
    assert len(insights["teams"]) == 20
    assert len(insights["team_profiles"]) == 20
    assert len(insights["snapshots"]) == insights["current_round"]
    assert insights["scorer_coverage"]["completed_matches"] == insights["scorer_coverage"]["matches_with_scorers"]
    assert all("streaks" in profile for profile in insights["team_profiles"].values())
    assert sorted(row["position"] for row in insights["snapshots"][-1]["table"]) == list(range(1, 21))


def test_generated_product_pages_exist_and_have_main_navigation_labels():
    insights = load("brasileirao_2026_insights.json")
    pages = [
        ROOT / "index.html",
        ROOT / "brasileirao" / "index.html",
        ROOT / "brasileirao" / "classificacao-rodada-a-rodada.html",
        ROOT / "brasileirao" / "artilharia-rodada-a-rodada.html",
        ROOT / "brasileirao" / "rankings-recordes.html",
    ]
    pages += [ROOT / "brasileirao" / "times" / f"{slug}.html" for slug in insights["team_profiles"]]
    pages += [ROOT / "brasileirao" / "rodadas" / f"rodada-{number}.html" for number in range(1, insights["current_round"] + 1)]
    assert all(path.exists() for path in pages)
    for path in pages:
        source = path.read_text(encoding="utf-8")
        assert 'aria-label="Navegação principal"' in source
        assert "<main" in source


def test_home_prioritizes_brasileirao_and_keeps_portfolio_navigable():
    source = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "A tabela tem memória" in source
    assert "Classificação" in source
    assert "Artilharia" in source
    assert 'href="projetos.html"' in source
    assert 'href="about.html"' in source


def test_generated_pages_have_social_images_and_large_twitter_cards():
    insights = load("brasileirao_2026_insights.json")
    pages = [
        ROOT / "index.html",
        ROOT / "brasileirao" / "classificacao-rodada-a-rodada.html",
        ROOT / "brasileirao" / "artilharia-rodada-a-rodada.html",
        ROOT / "brasileirao" / "comparador-times.html",
        ROOT / "brasileirao" / "rankings-recordes.html",
        ROOT / "brasileirao" / "times" / "palmeiras.html",
        ROOT / "brasileirao" / "rodadas" / f'rodada-{insights["current_round"]}.html',
    ]
    for path in pages:
        source = path.read_text(encoding="utf-8")
        assert '<meta property="og:image"' in source
        assert '<meta name="twitter:card" content="summary_large_image">' in source


def test_social_images_exist_with_expected_dimensions():
    from PIL import Image

    insights = load("brasileirao_2026_insights.json")
    paths = [
        ROOT / "assets" / "og" / "rodada-a-rodada.png",
        ROOT / "assets" / "og" / "classificacao.png",
        ROOT / "assets" / "og" / "artilharia.png",
        ROOT / "assets" / "og" / "comparador.png",
        ROOT / "assets" / "og" / "rankings-recordes.png",
        ROOT / "assets" / "og" / "times" / "palmeiras.png",
        ROOT / "assets" / "og" / "rodadas" / f'rodada-{insights["current_round"]}.png',
    ]
    for path in paths:
        assert path.exists()
        with Image.open(path) as image:
            assert image.size == (1200, 630)



def test_rankings_render_proportional_team_badges():
    rankings = (ROOT / "brasileirao" / "rankings-recordes.html").read_text(encoding="utf-8")
    home = (ROOT / "index.html").read_text(encoding="utf-8")
    assert rankings.count('class="br-team-badge"') == 36
    assert home.count("br-team-with-badge-chip") == 20
    assert home.count("br-team-with-badge-table") == 6
    assert home.count("br-team-with-badge-preview") == 4
    assert home.count("br-team-with-badge-headline") == 2
    for variant in ("cover", "ticker", "leader-card", "scorer"):
        assert home.count(f"br-team-with-badge-{variant}") == 1
    assert 'aria-hidden="true" width="48" height="48" loading="lazy" decoding="async"' in rankings
    assert rankings.count('alt=""') >= 36
    css = (ROOT / "style.css").read_text(encoding="utf-8")
    assert ".br-record-leaders strong .br-team-with-badge > span" in css



def test_standings_render_badges_initially_and_after_round_change():
    classification = (ROOT / "brasileirao" / "classificacao-rodada-a-rodada.html").read_text(encoding="utf-8")
    script = (ROOT / "brasileirao.js").read_text(encoding="utf-8")
    css = (ROOT / "style.css").read_text(encoding="utf-8")
    assert classification.count('class="br-team-badge"') == 20
    assert classification.count("br-team-with-badge-table") == 20
    assert classification.count("br-position-movement") == 20
    assert "Movimento desde a rodada anterior:" in classification
    assert 'const teamBadge = (team, variant = "inline") =>' in script
    assert '${teamBadge(row.team, "table")}' in script
    assert "function positionMovement(row, previousRows)" in script
    assert "previous?.table" in script
    assert 'aria-label="Manteve a posição"' in script
    assert ".br-position-movement.is-up" in css
    assert ".br-movement-key" in css


def test_team_badges_cover_hub_scorers_comparison_team_and_round_pages():
    insights = load("brasileirao_2026_insights.json")
    matches = load("serie_a_2026.json")["matches"]
    hub = (ROOT / "brasileirao" / "index.html").read_text(encoding="utf-8")
    scorers = (ROOT / "brasileirao" / "artilharia-rodada-a-rodada.html").read_text(encoding="utf-8")
    comparison = (ROOT / "brasileirao" / "comparador-times.html").read_text(encoding="utf-8")
    team = (ROOT / "brasileirao" / "times" / "flamengo.html").read_text(encoding="utf-8")
    latest_round = ROOT / "brasileirao" / "rodadas" / f'rodada-{insights["current_round"]}.html'
    round_source = latest_round.read_text(encoding="utf-8")
    script = (ROOT / "brasileirao.js").read_text(encoding="utf-8")
    matches_in_latest_round = sum(int(match["round"]) == insights["current_round"] for match in matches)

    assert hub.count("br-team-with-badge-chip") == 20
    assert scorers.count("br-team-with-badge-table") == len(insights["scorers"][-1]["ranking"])
    assert 'data-team-a-badge=""' in comparison
    assert 'data-team-b-badge=""' in comparison
    assert "br-team-with-badge-hero" in team
    assert "br-team-with-badge-form" in team
    assert "br-team-with-badge-heading" in team
    assert team.count("br-team-with-badge-nav") == 2
    assert matches_in_latest_round > 0
    assert round_source.count("br-team-with-badge-result-home") == matches_in_latest_round
    assert round_source.count("br-team-with-badge-result-away") == matches_in_latest_round
    for variant in ("legend", "scorer", "compare", "summary", "sentence"):
        assert f'teamBadge(row.team, "{variant}")' in script or f'teamBadge(profileA.team, "{variant}")' in script or f'teamBadge(leader.team, "{variant}")' in script or f'teamBadge(trailer.team, "{variant}")' in script


def test_partial_round_page_shows_results_and_full_upcoming_schedule():
    insights = load("brasileirao_2026_insights.json")
    source_dir = str(ROOT / "brasileirao_2026")
    sys.path.insert(0, source_dir)
    try:
        from build import round_content
    finally:
        sys.path.remove(source_dir)

    source_matches = load("serie_a_2026.json")["matches"][:2]
    matches = [
        {**source_matches[0], "score": "1 x 0", "date": "16/10/2026", "time": "19:00", "stadium": "Estádio A"},
        {**source_matches[1], "score": "-", "date": "17/10/2026", "time": "18:30", "stadium": "Estádio B"},
        {**source_matches[1], "score": "-", "date": "", "time": "", "stadium": ""},
    ]
    summary = {**insights["rounds"][-1], "leader_changed": False}
    table = insights["snapshots"][-1]["table"]
    source = round_content(99, 99, summary, matches, table)

    assert "Agenda e resultados" in source
    assert source.count('data-fixture-status="completed"') == 1
    assert source.count('data-fixture-status="scheduled"') == 2
    assert '<time datetime="2026-10-17T18:30:00-03:00">Sáb, 17 out</time>' in source
    assert "1 de 3 jogos concluídos" in source
    assert "Movimentos até aqui" in source
    assert "Classificação após os jogos concluídos" in source
    assert "segue na liderança até aqui" in source
    assert "18h30" in source
    assert "Estádio B" in source
    assert "Data a definir" in source
    assert "Local a definir" in source


def test_round_fixtures_link_both_teams_to_accessible_profiles():
    insights = load("brasileirao_2026_insights.json")
    matches = load("serie_a_2026.json")["matches"]
    current_round = insights["current_round"]
    round_matches = [match for match in matches if int(match["round"]) == current_round]
    source = (ROOT / "brasileirao" / "rodadas" / f"rodada-{current_round}.html").read_text(encoding="utf-8")
    css = (ROOT / "style.css").read_text(encoding="utf-8")

    assert source.count('class="br-fixture-team-link"') == len(round_matches) * 2
    for match in round_matches:
        for side in ("home", "away"):
            team = match[side]
            slug = re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", team).encode("ascii", "ignore").decode().lower()).strip("-")
            assert f'href="../times/{slug}.html" aria-label="Ver perfil do {team}"' in source
    assert ".br-fixture-team-link:focus-visible" in css
    assert "min-height: 44px" in css


def test_only_home_leader_card_uses_current_leader_color():
    home = (ROOT / "index.html").read_text(encoding="utf-8")
    hub = (ROOT / "brasileirao/index.html").read_text(encoding="utf-8")
    body = re.search(r'<body class="br-page br-home" style="([^"]+)">', home)
    assert body
    color = re.search(r"--br-leader-color:(#[0-9a-f]{6})", body.group(1))
    assert color
    assert '<meta name="theme-color" content="#101714">' in home
    assert "--br-leader-color" not in hub
    assert "br-leader-theme" not in home + hub

    css = (ROOT / "style.css").read_text(encoding="utf-8")
    assert "background: var(--br-leader-color)" in css
    assert "color: var(--br-leader-text)" in css
    assert ".br-leader-theme" not in css


def test_team_badges_stay_close_to_team_names():
    css = (ROOT / "style.css").read_text(encoding="utf-8")
    rule = re.search(r"^\.br-team-with-badge \{([^}]+)\}", css, re.MULTILINE)
    assert rule
    assert "gap: clamp(4px, .24em, 12px)" in rule.group(1)



def test_home_leader_name_never_breaks_inside_the_club_name():
    home = (ROOT / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "style.css").read_text(encoding="utf-8")
    assert 'class="br-leader-name"' in home
    assert ".br-ranking-card .br-leader-name" in css
    assert "white-space: nowrap" in css


def test_shared_site_script_loads_plausible_only_on_production():
    source = (ROOT / "site.js").read_text(encoding="utf-8")
    assert "'brasileiraoemrodadas.com.br'" in source
    assert "'www.brasileiraoemrodadas.com.br'" in source
    assert "analyticsHosts.includes(location.hostname)" in source
    assert "https://plausible.io/js/script.js" in source



def test_standings_abbreviations_have_accessible_tooltips():
    script = (ROOT / "brasileirao.js").read_text(encoding="utf-8")
    css = (ROOT / "style.css").read_text(encoding="utf-8")
    for abbreviation, label in {
        "Pts": "Pontos",
        "J": "Jogos disputados",
        "V": "Vitórias",
        "E": "Empates",
        "D": "Derrotas",
        "SG": "Saldo de gols",
    }.items():
        assert f'"{abbreviation}": "{label}"' in script
    assert 'querySelectorAll("[data-standings-table] thead th")' in script
    assert 'trigger.setAttribute("aria-label"' in script
    assert 'event.key === "Escape"' in script
    assert ".br-tooltip-trigger:focus-visible" in css
    assert ".br-tooltip-bubble" in css



def test_team_finder_is_accessible_progressive_and_filters_names():
    home = (ROOT / "index.html").read_text(encoding="utf-8")
    hub = (ROOT / "brasileirao/index.html").read_text(encoding="utf-8")
    script = (ROOT / "brasileirao.js").read_text(encoding="utf-8")
    css = (ROOT / "style.css").read_text(encoding="utf-8")

    for source, suffix in ((home, "home"), (hub, "hub")):
        assert f'id="team-search-{suffix}"' in source
        assert f'aria-controls="team-list-{suffix}"' in source
        assert f'aria-describedby="team-search-status-{suffix}"' in source
        assert 'data-team-finder' in source
        assert source.count('class="br-team-chip"') == 20

    assert '<script src="../brasileirao.js" defer></script>' in hub
    assert 'normalize("NFD")' in script
    assert '.includes(query)' in script
    assert 'event.key === "Escape"' in script
    assert 'visible === 1 ? "time encontrado" : "times encontrados"' in script
    assert ".br-team-chip[hidden]" in css
    assert ".br-team-search-row:focus-within" in css


def test_team_finder_filters_accent_insensitively_in_browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto((ROOT / "brasileirao/index.html").as_uri(), wait_until="domcontentloaded")
        search = page.locator("#team-search-hub")
        assert search.is_visible()

        search.fill("sao")
        visible = page.locator("#team-list-hub .br-team-chip:visible")
        assert visible.count() == 1
        assert "São Paulo" in visible.first.text_content()
        assert page.locator("#team-search-status-hub").text_content() == "1 time encontrado."

        search.fill("time inexistente")
        assert page.locator("#team-list-hub .br-team-chip:visible").count() == 0
        assert page.locator("#team-empty-hub").is_visible()

        page.locator("[data-team-search-clear]").click()
        assert page.locator("#team-list-hub .br-team-chip:visible").count() == 20
        assert page.locator("#team-search-status-hub").text_content() == "20 times disponíveis."
        browser.close()


def test_round_archive_jump_is_accessible_and_preserves_static_links():
    insights = load("brasileirao_2026_insights.json")
    current_round = insights["current_round"]
    home = (ROOT / "index.html").read_text(encoding="utf-8")
    hub = (ROOT / "brasileirao/index.html").read_text(encoding="utf-8")
    script = (ROOT / "brasileirao.js").read_text(encoding="utf-8")
    css = (ROOT / "style.css").read_text(encoding="utf-8")

    for source, suffix, prefix in (
        (home, "home", "brasileirao/rodadas/"),
        (hub, "hub", "rodadas/"),
    ):
        assert 'data-round-jump' in source
        assert 'hidden novalidate' in source
        assert f'data-round-prefix="{prefix}"' in source
        assert f'id="round-jump-{suffix}"' in source
        assert f'max="{current_round}"' in source
        assert f'aria-describedby="round-jump-status-{suffix}"' in source
        assert source.count('class="br-round-links"') == 1
        assert source.count('Rodada ') >= current_round

    assert 'form.hidden = false' in script
    assert 'input.setAttribute("aria-invalid", "true")' in script
    assert 'Escolha uma rodada entre ${minimum} e ${maximum}.' in script
    assert 'location.assign(new URL(' in script
    assert '.br-round-jump input:focus-visible' in css
    assert '.br-round-jump input[aria-invalid="true"]' in css


def test_round_archive_jump_validates_and_opens_round_in_browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto((ROOT / "brasileirao/index.html").as_uri(), wait_until="domcontentloaded")
        jump = page.locator("#round-jump-hub")
        assert jump.is_visible()

        jump.fill("999")
        page.locator("[data-round-jump] button").click()
        assert jump.get_attribute("aria-invalid") == "true"
        assert "Escolha uma rodada entre" in page.locator("#round-jump-status-hub").text_content()

        jump.fill("2")
        page.locator("[data-round-jump] button").click()
        page.wait_for_url("**/rodadas/rodada-2.html")
        assert page.url.endswith("/rodadas/rodada-2.html")
        browser.close()


def test_scorer_finder_is_accessible_progressive_and_keeps_static_fallback():
    page = (ROOT / "brasileirao" / "artilharia-rodada-a-rodada.html").read_text(encoding="utf-8")
    script = (ROOT / "brasileirao.js").read_text(encoding="utf-8")
    css = (ROOT / "style.css").read_text(encoding="utf-8")

    assert 'data-scorer-finder hidden' in page
    assert 'id="scorer-search"' in page
    assert 'aria-controls="scorer-table-body"' in page
    assert 'aria-describedby="scorer-search-status"' in page
    assert 'data-scorer-empty hidden' in page
    assert page.count("<tr>") > 1
    assert "function initScorerFinder(table)" in script
    assert "normalizeTeamSearch(playerAndTeam).includes(query)" in script
    assert 'visible === 1 ? "jogador encontrado" : "jogadores encontrados"' in script
    assert "applyScorerFilter();" in script
    assert ".br-scorer-search-row:focus-within" in css
    assert ".br-scorer-table tbody tr[hidden]" in css



def test_round_selectors_keep_shareable_url_state():
    source = (ROOT / "brasileirao.js").read_text(encoding="utf-8")
    assert 'searchParams.get("rodada")' in source
    assert 'searchParams.set("rodada", select.value)' in source
    assert 'history.pushState({ rodada: select.value }' in source
    assert source.count('window.addEventListener("popstate"') >= 2
    assert source.count("restoreRoundFromUrl(roundSelect, defaultRound)") == 2
    assert source.count("restoreRoundFromUrl(scorerSelect, defaultRound)") == 2
    assert 'hasRoundOption(select, requested)' in source


def test_round_views_offer_accessible_native_share_with_copy_fallback():
    source = (ROOT / "brasileirao.js").read_text(encoding="utf-8")
    css = (ROOT / "style.css").read_text(encoding="utf-8")
    assert 'data-round-share-button' in source
    assert 'data-round-share-status aria-live="polite"' in source
    assert 'navigator.share(shareData)' in source
    assert 'navigator.clipboard.writeText(shareUrl.href)' in source
    assert 'shareUrl.searchParams.set("time", focusedTeam)' in source
    assert source.count("initRoundShare(") == 3
    assert ".br-view-share button:focus-visible" in css
    assert ".br-view-share-status" in css


def test_round_steppers_are_accessible_and_keep_the_select_as_fallback():
    source = (ROOT / "brasileirao.js").read_text(encoding="utf-8")
    css = (ROOT / "style.css").read_text(encoding="utf-8")
    assert 'navigation.setAttribute("aria-label", "Navegação entre rodadas")' in source
    assert 'data-round-previous' in source
    assert 'data-round-next' in source
    assert 'select.dispatchEvent(new Event("change", { bubbles: true }))' in source
    assert "previous.disabled = !previousOption" in source
    assert "next.disabled = !nextOption" in source
    assert source.count("initRoundStepper(") == 3
    assert ".br-round-stepper button:disabled" in css
    assert ".br-round-stepper button:focus-visible" in css


def test_round_archive_has_progressive_previous_and_next_navigation():
    insights = load("brasileirao_2026_insights.json")
    current_round = insights["current_round"]
    first = (ROOT / "brasileirao/rodadas/rodada-1.html").read_text(encoding="utf-8")
    middle = (ROOT / "brasileirao/rodadas/rodada-2.html").read_text(encoding="utf-8")
    latest = (ROOT / "brasileirao/rodadas" / f"rodada-{current_round}.html").read_text(encoding="utf-8")
    css = (ROOT / "style.css").read_text(encoding="utf-8")

    for source in (first, middle, latest):
        assert 'aria-label="Navegação entre resumos de rodadas"' in source
        assert 'href="../index.html#rodadas"' in source
        assert "Todas as rodadas" in source
    assert 'rel="prev"' not in first
    assert 'rel="next" href="rodada-2.html"' in first
    assert 'rel="prev" href="rodada-1.html"' in middle
    assert 'rel="next" href="rodada-3.html"' in middle
    assert f'aria-current="page">Rodada {current_round} de {current_round}' in latest
    assert 'rel="next"' not in latest
    assert f'rel="prev" href="rodada-{current_round - 1}.html"' in latest
    assert ".br-round-pagination a:focus-visible" in css
    assert "grid-template-columns: 1fr auto 1fr" in css




def test_wide_tables_offer_accessible_scroll_controls():
    source = (ROOT / "brasileirao.js").read_text(encoding="utf-8")
    css = (ROOT / "style.css").read_text(encoding="utf-8")
    assert 'wrapper.setAttribute("role", "region")' in source
    assert 'data-table-scroll-previous' in source
    assert 'data-table-scroll-next' in source
    assert 'ResizeObserver' in source
    assert 'prefers-reduced-motion: reduce' in source
    assert ".br-table-scroll-tools button:focus-visible" in css
    assert '.br-table-wrap[tabindex="0"]:focus-visible' in css
    assert ".br-table-scroll-tools[hidden]" in css
    assert ".br-table[data-standings-table]" in css
    assert "width: 720px" in css
    assert "min-width: 720px" in css
    assert ".br-analysis-grid > *" in css


def test_standings_team_focus_is_accessible_persistent_and_shareable():
    source = (ROOT / "brasileirao.js").read_text(encoding="utf-8")
    css = (ROOT / "style.css").read_text(encoding="utf-8")
    assert 'data-team-focus-select' in source
    assert 'aria-live="polite"' in source
    assert 'searchParams.set("time", selected)' in source
    assert 'localStorage.setItem(teamFocusStorageKey, selected)' in source
    assert 'link.setAttribute("aria-current", "true")' in source
    assert 'prefers-reduced-motion: reduce' in source
    assert ".br-table tbody tr.is-focused" in css
    assert ".br-team-focus a:focus-visible" in css
    assert "@media (max-width: 720px)" in css


def test_round_views_expose_loading_and_recoverable_error_states():
    source = (ROOT / "brasileirao.js").read_text(encoding="utf-8")
    css = (ROOT / "style.css").read_text(encoding="utf-8")
    assert 'target.setAttribute("aria-busy", "true")' in source
    assert 'role="status"' in source
    assert 'role="alert"' in source
    assert 'data-round-reload' in source
    assert source.count('setRoundViewState(') == 7
    assert ".br-load-state" in css
    assert "@keyframes br-spin" in css
    assert "@media (prefers-reduced-motion: reduce)" in css


def test_round_selectors_restore_url_and_browser_history():
    from functools import partial
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread
    from playwright.sync_api import sync_playwright

    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        partial(QuietHandler, directory=str(ROOT)),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            page.add_init_script("""
              Object.defineProperty(navigator, "share", { configurable: true, value: undefined });
              Object.defineProperty(navigator, "clipboard", {
                configurable: true,
                value: { writeText: async value => { window.__copiedUrl = value; } },
              });
            """)

            page.goto(
                f"{base_url}/brasileirao/classificacao-rodada-a-rodada.html?rodada=10",
                wait_until="domcontentloaded",
            )
            standings = page.locator("[data-round-select]")
            page.wait_for_function("document.querySelector('[data-round-select]').value === '10'")
            movement = page.locator("[data-standings-table] .br-position-movement")
            assert movement.count() == 20
            assert page.locator("[data-standings-table] .br-position-movement.is-up, [data-standings-table] .br-position-movement.is-down").count() > 0
            standings.select_option("11")
            page.wait_for_url("**?rodada=11")
            page.go_back()
            page.wait_for_function("document.querySelector('[data-round-select]').value === '10'")

            team_focus = page.locator("[data-team-focus-select]")
            assert team_focus.is_visible()
            team_focus.select_option("flamengo")
            page.wait_for_url("**time=flamengo")
            focused_row = page.locator("[data-standings-table] tbody tr.is-focused")
            assert focused_row.count() == 1
            assert "Flamengo" in focused_row.text_content()
            assert focused_row.locator("th a").get_attribute("aria-current") == "true"
            assert "Flamengo:" in page.locator("[data-team-focus-status]").text_content()
            assert page.evaluate("localStorage.getItem('brasileirao-team-focus')") == "flamengo"

            standings.select_option("12")
            page.wait_for_url("**rodada=12&time=flamengo")
            assert "Flamengo" in page.locator("[data-standings-table] tbody tr.is-focused").text_content()

            page.goto(
                f"{base_url}/brasileirao/classificacao-rodada-a-rodada.html?rodada=12",
                wait_until="domcontentloaded",
            )
            page.wait_for_function("document.querySelector('[data-team-focus-select]').value === 'flamengo'")
            assert "Flamengo" in page.locator("[data-standings-table] tbody tr.is-focused").text_content()
            standings_share = page.locator("[data-round-share-button]")
            assert standings_share.is_visible()
            standings_share.click()
            page.wait_for_function("window.__copiedUrl?.includes('rodada=12')")
            assert "time=flamengo" in page.evaluate("window.__copiedUrl")
            assert page.locator("[data-round-share-status]").text_content() == "Link copiado."

            page.goto(
                f"{base_url}/brasileirao/artilharia-rodada-a-rodada.html?rodada=5",
                wait_until="domcontentloaded",
            )
            scorers = page.locator("[data-scorer-round-select]")
            page.wait_for_function("document.querySelector('[data-scorer-round-select]').value === '5'")
            scorer_finder = page.locator("[data-scorer-finder]")
            scorer_finder.wait_for(state="visible")
            scorer_search = page.locator("[data-scorer-search]")
            total_scorers = page.locator("[data-scorer-table] tbody tr").count()
            scorer_search.fill("vinicius")
            visible_scorers = page.locator("[data-scorer-table] tbody tr:visible")
            assert visible_scorers.count() == 1
            assert "Carlos Vinícius" in visible_scorers.first.text_content()
            assert page.locator("#scorer-search-status").text_content() == "1 jogador encontrado."

            scorer_search.fill("jogador inexistente")
            assert visible_scorers.count() == 0
            assert page.locator("[data-scorer-empty]").is_visible()
            scorer_search.press("Escape")
            assert scorer_search.input_value() == ""
            assert visible_scorers.count() == total_scorers

            scorer_search.fill("palmeiras")
            previous = page.locator("[data-round-previous]")
            next_round = page.locator("[data-round-next]")
            assert previous.is_visible()
            assert next_round.is_visible()
            next_round.click()
            page.wait_for_url("**?rodada=6")
            assert scorers.input_value() == "6"
            assert scorer_search.input_value() == "palmeiras"
            assert visible_scorers.count() > 0
            page.go_back()
            page.wait_for_function("document.querySelector('[data-scorer-round-select]').value === '5'")
            page.locator("[data-round-share-button]").click()
            page.wait_for_function("window.__copiedUrl?.includes('rodada=5')")
            assert page.locator("[data-round-share-status]").text_content() == "Link copiado."

            mobile_page = browser.new_page(viewport={"width": 390, "height": 844})
            mobile_page.bring_to_front()
            mobile_page.goto(
                f"{base_url}/brasileirao/classificacao-rodada-a-rodada.html",
                wait_until="domcontentloaded",
            )
            scroll_tools = mobile_page.locator("[data-table-scroll-tools]").first
            scroll_tools.wait_for(state="visible")
            scroll_previous = scroll_tools.locator("[data-table-scroll-previous]")
            scroll_next = scroll_tools.locator("[data-table-scroll-next]")
            assert scroll_previous.is_disabled()
            assert scroll_next.is_enabled()
            scroll_next.click()
            mobile_page.wait_for_function(
                "document.querySelector('.br-table-wrap').scrollLeft > 0"
            )
            mobile_page.wait_for_function(
                "!document.querySelector('[data-table-scroll-previous]').disabled"
            )
            assert scroll_previous.is_enabled()

            error_page = browser.new_page()
            error_page.route(
                "**/data/brasileirao_2026_insights.json",
                lambda route: route.fulfill(status=503, body="{}"),
            )
            error_page.goto(
                f"{base_url}/brasileirao/classificacao-rodada-a-rodada.html",
                wait_until="domcontentloaded",
            )
            alert = error_page.locator(".br-load-error[role='alert']")
            assert alert.is_visible()
            assert error_page.locator("[data-round-select]").is_disabled()
            assert error_page.locator("[data-round-reload]").is_visible()

            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
