import json
import re
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
    assert home.count('class="br-team-badge"') >= 38
    assert 'aria-hidden="true" width="48" height="48" loading="lazy" decoding="async"' in rankings
    assert rankings.count('alt=""') >= 36
    css = (ROOT / "style.css").read_text(encoding="utf-8")
    assert ".br-record-leaders strong .br-team-with-badge > span" in css



def test_standings_render_badges_initially_and_after_round_change():
    classification = (ROOT / "brasileirao" / "classificacao-rodada-a-rodada.html").read_text(encoding="utf-8")
    script = (ROOT / "brasileirao.js").read_text(encoding="utf-8")
    assert classification.count('class="br-team-badge"') == 20
    assert classification.count("br-team-with-badge-table") == 20
    assert 'const teamBadge = (team, variant = "inline") =>' in script
    assert '${teamBadge(row.team, "table")}' in script


def test_team_badges_cover_hub_scorers_comparison_team_and_round_pages():
    insights = load("brasileirao_2026_insights.json")
    hub = (ROOT / "brasileirao" / "index.html").read_text(encoding="utf-8")
    scorers = (ROOT / "brasileirao" / "artilharia-rodada-a-rodada.html").read_text(encoding="utf-8")
    comparison = (ROOT / "brasileirao" / "comparador-times.html").read_text(encoding="utf-8")
    team = (ROOT / "brasileirao" / "times" / "flamengo.html").read_text(encoding="utf-8")
    latest_round = ROOT / "brasileirao" / "rodadas" / f'rodada-{insights["current_round"]}.html'
    round_source = latest_round.read_text(encoding="utf-8")
    script = (ROOT / "brasileirao.js").read_text(encoding="utf-8")

    assert hub.count("br-team-with-badge-chip") == 20
    assert scorers.count("br-team-with-badge-table") == len(insights["scorers"][-1]["ranking"])
    assert 'data-team-a-badge=""' in comparison
    assert 'data-team-b-badge=""' in comparison
    assert "br-team-with-badge-hero" in team
    assert "br-team-with-badge-form" in team
    assert "br-team-with-badge-heading" in team
    assert team.count("br-team-with-badge-nav") == 2
    assert round_source.count("br-team-with-badge-result-home") == 10
    assert round_source.count("br-team-with-badge-result-away") == 10
    for variant in ("legend", "scorer", "compare", "summary", "sentence"):
        assert f'teamBadge(row.team, "{variant}")' in script or f'teamBadge(profileA.team, "{variant}")' in script or f'teamBadge(leader.team, "{variant}")' in script or f'teamBadge(trailer.team, "{variant}")' in script


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
    assert "location.hostname === 'felandim.github.io'" in source
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



def test_round_selectors_keep_shareable_url_state():
    source = (ROOT / "brasileirao.js").read_text(encoding="utf-8")
    assert 'searchParams.get("rodada")' in source
    assert 'searchParams.set("rodada", select.value)' in source
    assert 'history.pushState({ rodada: select.value }' in source
    assert source.count('window.addEventListener("popstate"') >= 2
    assert source.count("restoreRoundFromUrl(roundSelect, defaultRound)") == 2
    assert source.count("restoreRoundFromUrl(scorerSelect, defaultRound)") == 2
    assert 'hasRoundOption(select, requested)' in source


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

            page.goto(
                f"{base_url}/brasileirao/classificacao-rodada-a-rodada.html?rodada=10",
                wait_until="domcontentloaded",
            )
            standings = page.locator("[data-round-select]")
            page.wait_for_function("document.querySelector('[data-round-select]').value === '10'")
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

            page.goto(
                f"{base_url}/brasileirao/artilharia-rodada-a-rodada.html?rodada=5",
                wait_until="domcontentloaded",
            )
            scorers = page.locator("[data-scorer-round-select]")
            page.wait_for_function("document.querySelector('[data-scorer-round-select]').value === '5'")
            previous = page.locator("[data-round-previous]")
            next_round = page.locator("[data-round-next]")
            assert previous.is_visible()
            assert next_round.is_visible()
            next_round.click()
            page.wait_for_url("**?rodada=6")
            assert scorers.input_value() == "6"
            page.go_back()
            page.wait_for_function("document.querySelector('[data-scorer-round-select]').value === '5'")

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
