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
    assert sorted(row["position"] for row in insights["snapshots"][-1]["table"]) == list(range(1, 21))


def test_generated_product_pages_exist_and_have_main_navigation_labels():
    insights = load("brasileirao_2026_insights.json")
    pages = [
        ROOT / "index.html",
        ROOT / "brasileirao" / "index.html",
        ROOT / "brasileirao" / "classificacao-rodada-a-rodada.html",
        ROOT / "brasileirao" / "artilharia-rodada-a-rodada.html",
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
