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
    assert home.count('class="br-team-badge"') == 4
    assert 'aria-hidden="true" width="48" height="48" loading="lazy" decoding="async"' in rankings
    assert rankings.count('alt=""') >= 36
    css = (ROOT / "style.css").read_text(encoding="utf-8")
    assert ".br-record-leaders strong .br-team-with-badge > span" in css


def test_shared_site_script_loads_plausible_only_on_production():
    source = (ROOT / "site.js").read_text(encoding="utf-8")
    assert "location.hostname === 'felandim.github.io'" in source
    assert "https://plausible.io/js/script.js" in source
