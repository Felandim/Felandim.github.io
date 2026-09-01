#!/usr/bin/env python3
"""Gera e publica o resumo diário do Brasileirão por Rodadas no Instagram."""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
INSIGHTS_FILE = ROOT / "data" / "brasileirao_2026_insights.json"
MATCHES_FILE = ROOT / "data" / "serie_a_2026.json"
DEFAULT_OUTPUT = ROOT / "assets" / "instagram" / "daily.png"
TZ = ZoneInfo("America/Sao_Paulo")
SITE_URL = "brasileiraoemrodadas.com.br"
GRAPH_HOST = "https://graph.instagram.com"
DEFAULT_API_VERSION = "v23.0"

BG = "#0f1714"
PANEL = "#18231f"
TEXT = "#f4f7f5"
MUTED = "#aebbb5"
ACCENT = "#64d98b"
RED = "#ff827b"


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    paths = [Path("/usr/share/fonts/truetype/dejavu") / name, Path("/usr/share/fonts/dejavu") / name]
    for path in paths:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def load_insights(path: Path = INSIGHTS_FILE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_matches(path: Path = MATCHES_FILE) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["matches"]


def current_snapshot(insights: dict) -> tuple[dict, dict]:
    if not insights.get("snapshots") or not insights.get("rounds"):
        raise ValueError("Insights sem rodadas concluídas.")
    return insights["snapshots"][-1], insights["rounds"][-1]


def _join_teams(values: list[str], empty: str = "ninguém") -> str:
    return ", ".join(values) if values else empty


def _score(value: str) -> tuple[int, int] | None:
    match = re.fullmatch(r"\s*(\d+)\s*x\s*(\d+)\s*", value or "")
    return (int(match.group(1)), int(match.group(2))) if match else None


def position_movements(insights: dict) -> dict[str, int]:
    """Retorna quantas posições cada time ganhou/perdeu desde o snapshot anterior."""
    snapshots = insights.get("snapshots", [])
    if len(snapshots) < 2:
        return {}
    previous = {row["team"]: row["position"] for row in snapshots[-2]["table"]}
    current = {row["team"]: row["position"] for row in snapshots[-1]["table"]}
    return {team: previous[team] - position for team, position in current.items() if team in previous}


def movement_label(delta: int) -> str:
    if delta > 0:
        return f"▲{delta}"
    if delta < 0:
        return f"▼{abs(delta)}"
    return "•"


def five_round_form(insights: dict) -> dict | None:
    snapshots = insights.get("snapshots", [])
    if len(snapshots) < 6:
        return None
    latest = snapshots[-1]
    base = snapshots[-6]
    base_by_team = {row["team"]: row for row in base["table"]}
    candidates = []
    for row in latest["table"]:
        previous = base_by_team.get(row["team"])
        if previous is None:
            continue
        candidates.append({
            "team": row["team"],
            "points": row["points"] - previous["points"],
            "position_gain": previous["position"] - row["position"],
        })
    if not candidates:
        return None
    best_points = max(item["points"] for item in candidates)
    leaders = [item for item in candidates if item["points"] == best_points]
    leaders.sort(key=lambda item: (-item["position_gain"], item["team"]))
    return {
        "teams": [item["team"] for item in leaders],
        "points": best_points,
        "from_round": base["round"],
        "to_round": latest["round"],
    }


def round_upset(insights: dict, matches: list[dict], minimum_position_gap: int = 5) -> dict | None:
    """Encontra a maior zebra: vencedor que iniciou a rodada bem abaixo do derrotado."""
    snapshots = insights.get("snapshots", [])
    rounds = insights.get("rounds", [])
    if len(snapshots) < 2 or not rounds:
        return None

    latest_round = int(rounds[-1]["round"])
    previous_positions = {row["team"]: row["position"] for row in snapshots[-2]["table"]}
    candidates = []

    for match in matches:
        if int(match.get("round", 0)) != latest_round:
            continue
        score = _score(match.get("score", ""))
        if not score or score[0] == score[1]:
            continue
        winner = match["home"] if score[0] > score[1] else match["away"]
        loser = match["away"] if winner == match["home"] else match["home"]
        if winner not in previous_positions or loser not in previous_positions:
            continue
        position_gap = previous_positions[winner] - previous_positions[loser]
        if position_gap < minimum_position_gap:
            continue
        candidates.append({
            "winner": winner,
            "loser": loser,
            "winner_position": previous_positions[winner],
            "loser_position": previous_positions[loser],
            "position_gap": position_gap,
            "home": match["home"],
            "away": match["away"],
            "score": match["score"],
            "goal_margin": abs(score[0] - score[1]),
        })

    if not candidates:
        return None
    return max(candidates, key=lambda item: (item["position_gap"], item["goal_margin"], item["winner"]))


def table_hook(insights: dict) -> str:
    snapshot, _ = current_snapshot(insights)
    table = snapshot["table"]
    if len(table) < 17:
        return "A tabela segue em movimento"
    battles = [
        (table[0]["points"] - table[1]["points"], 0, "title"),
        (table[3]["points"] - table[4]["points"], 1, "g4"),
        (table[15]["points"] - table[16]["points"], 2, "z4"),
    ]
    gap, _, battle = min(battles, key=lambda item: (item[0], item[1]))
    unit = "ponto" if gap == 1 else "pontos"
    if battle == "title":
        return f"Liderança separada por {gap} {unit}"
    if battle == "g4":
        return f"Só {gap} {unit} separa o G4 do 5º"
    return f"Só {gap} {unit} separa permanência e Z4"


def boundary_cluster(insights: dict, maximum_gap: int = 3, minimum_teams: int = 3) -> dict | None:
    """Detecta pelotões comprimidos nos cortes do G4 e do Z4."""
    snapshot, _ = current_snapshot(insights)
    table = snapshot["table"]
    if len(table) < 17:
        return None

    g4_cutoff = table[3]["points"]
    g4_rows = [row for row in table[3:] if 0 <= g4_cutoff - row["points"] <= maximum_gap]
    z4_cutoff = table[15]["points"]
    z4_rows = [row for row in table[15:] if 0 <= z4_cutoff - row["points"] <= maximum_gap]

    candidates = []
    if len(g4_rows) >= minimum_teams:
        spread = g4_cutoff - g4_rows[-1]["points"]
        candidates.append({
            "kind": "g4_cluster",
            "count": len(g4_rows),
            "spread": spread,
            "label": "G4 EMBOLADO",
            "text": f"{len(g4_rows)} times em até {spread} {'ponto' if spread == 1 else 'pontos'} do 4º",
            "caption": f"G4 embolado: {len(g4_rows)} times estão em uma faixa de {spread} {'ponto' if spread == 1 else 'pontos'} a partir do 4º colocado.",
        })
    if len(z4_rows) >= minimum_teams:
        spread = z4_cutoff - z4_rows[-1]["points"]
        candidates.append({
            "kind": "z4_cluster",
            "count": len(z4_rows),
            "spread": spread,
            "label": "Z4 EMBOLADO",
            "text": f"{len(z4_rows)} times em até {spread} {'ponto' if spread == 1 else 'pontos'} da permanência",
            "caption": f"Z4 embolado: {len(z4_rows)} times estão em uma faixa de {spread} {'ponto' if spread == 1 else 'pontos'} a partir do 16º colocado.",
        })
    if not candidates:
        return None
    return max(candidates, key=lambda item: (item["count"], -item["spread"], item["kind"] == "g4_cluster"))


def boundary_pressure(insights: dict, maximum_gap: int = 3) -> dict | None:
    """Personaliza a menor distância até G4 ou saída do Z4 quando cabe em um resultado."""
    snapshot, _ = current_snapshot(insights)
    table = snapshot["table"]
    if len(table) < 17:
        return None

    candidates = [
        {
            "kind": "g4_pressure",
            "team": table[4]["team"],
            "gap": table[3]["points"] - table[4]["points"],
            "target": table[3]["team"],
        },
        {
            "kind": "z4_pressure",
            "team": table[16]["team"],
            "gap": table[15]["points"] - table[16]["points"],
            "target": table[15]["team"],
        },
    ]
    candidates = [item for item in candidates if 0 <= item["gap"] <= maximum_gap]
    if not candidates:
        return None

    pressure = min(candidates, key=lambda item: (item["gap"], 0 if item["kind"] == "g4_pressure" else 1))
    gap, team = pressure["gap"], pressure["team"]
    if pressure["kind"] == "g4_pressure":
        text = f"{team} está empatado em pontos com o G4" if gap == 0 else f"{team} está a {gap} {'ponto' if gap == 1 else 'pontos'} do G4"
        caption = f"Na cola do G4: {team} está empatado em pontos com o 4º colocado." if gap == 0 else f"Na cola do G4: {team} está a {gap} {'ponto' if gap == 1 else 'pontos'} do 4º colocado."
        label = "NA COLA DO G4"
    else:
        text = f"{team} está empatado em pontos com o 16º" if gap == 0 else f"{team} está a {gap} {'ponto' if gap == 1 else 'pontos'} de sair do Z4"
        caption = f"Pressão no Z4: {team} está empatado em pontos com o 16º colocado." if gap == 0 else f"Pressão no Z4: {team} está a {gap} {'ponto' if gap == 1 else 'pontos'} de sair da zona."
        label = "PRESSÃO NO Z4"
    return {**pressure, "label": label, "text": text, "caption": caption}


def round_spotlight(insights: dict, matches: list[dict] | None = None) -> dict:
    _, latest = current_snapshot(insights)
    if latest.get("leader_changed") and latest.get("leader"):
        return {
            "kind": "leader",
            "label": "NOVO LÍDER",
            "text": f"{latest['leader']} assumiu a ponta",
            "caption": f"Mudança na liderança: {latest['leader']} assumiu a ponta.",
        }

    g4_in, g4_out = latest.get("g4_in", []), latest.get("g4_out", [])
    if g4_in or g4_out:
        if g4_in and g4_out:
            text = f"{_join_teams(g4_in)} entrou • {_join_teams(g4_out)} saiu"
            caption = f"Mudou o G4: {_join_teams(g4_in)} entrou; {_join_teams(g4_out)} saiu."
        elif g4_in:
            text, caption = f"{_join_teams(g4_in)} entrou no G4", f"Mudou o G4: {_join_teams(g4_in)} entrou."
        else:
            text, caption = f"{_join_teams(g4_out)} saiu do G4", f"Mudou o G4: {_join_teams(g4_out)} saiu."
        return {"kind": "g4", "label": "MUDANÇA NO G4", "text": text, "caption": caption}

    z4_in, z4_out = latest.get("z4_in", []), latest.get("z4_out", [])
    if z4_in or z4_out:
        if z4_in and z4_out:
            text = f"{_join_teams(z4_out)} saiu • {_join_teams(z4_in)} entrou"
            caption = f"Mudou o Z4: {_join_teams(z4_out)} saiu; {_join_teams(z4_in)} entrou."
        elif z4_out:
            text, caption = f"{_join_teams(z4_out)} saiu do Z4", f"Mudou o Z4: {_join_teams(z4_out)} saiu."
        else:
            text, caption = f"{_join_teams(z4_in)} entrou no Z4", f"Mudou o Z4: {_join_teams(z4_in)} entrou."
        return {"kind": "z4", "label": "MUDANÇA NO Z4", "text": text, "caption": caption}

    upset = round_upset(insights, matches or [])
    if upset:
        return {
            "kind": "upset",
            "label": "ZEBRA DA RODADA",
            "text": f"{upset['winner']} bateu o {upset['loser']} • diferença de {upset['position_gap']} posições",
            "caption": (
                f"Zebra da rodada: o {upset['winner']} ({upset['winner_position']}º antes da rodada) "
                f"venceu o {upset['loser']} ({upset['loser_position']}º)."
            ),
        }

    cluster = boundary_cluster(insights)
    if cluster:
        return cluster

    pressure = boundary_pressure(insights)
    if pressure:
        return pressure

    biggest = latest.get("biggest_win")
    if biggest and biggest.get("winner") != "Empate" and biggest.get("margin", 0) >= 3:
        return {
            "kind": "biggest_win",
            "label": "DESTAQUE DA RODADA",
            "text": f"{biggest['home']} {biggest['score']} {biggest['away']}",
            "caption": "",
        }

    form = five_round_form(insights)
    if form:
        teams = _join_teams(form["teams"][:2]) + (" + outros" if len(form["teams"]) > 2 else "")
        return {
            "kind": "form",
            "label": "EM ALTA • ÚLTIMAS 5 RODADAS",
            "text": f"{teams} • {form['points']} pontos",
            "caption": "",
        }
    return {"kind": "goals", "label": "NÚMERO DA RODADA", "text": f"{latest['goals']} gols na rodada", "caption": ""}


def build_caption(insights: dict, matches: list[dict] | None = None) -> str:
    snapshot, latest = current_snapshot(insights)
    table = snapshot["table"]
    leader = table[0]
    lines = [
        table_hook(insights) + ".",
        f"Brasileirão {insights['season']} — rodada {latest['round']}" + (" (parcial)." if latest.get("matches", 10) < 10 else "."),
        "",
        f"Líder: {leader['team']} — {leader['points']} pts.",
        f"G4: {', '.join(row['team'] for row in table[:4])}.",
        f"Z4: {', '.join(row['team'] for row in table[-4:])}.",
        f"Gols na rodada: {latest['goals']}.",
    ]

    spotlight = round_spotlight(insights, matches)
    if spotlight["caption"]:
        lines.append(spotlight["caption"])

    upset = round_upset(insights, matches or [])
    if upset and spotlight["kind"] != "upset":
        lines.append(
            f"Zebra da rodada: o {upset['winner']} ({upset['winner_position']}º antes da rodada) "
            f"venceu o {upset['loser']} ({upset['loser_position']}º)."
        )

    cluster = boundary_cluster(insights)
    if cluster and spotlight["kind"] != cluster["kind"]:
        lines.append(cluster["caption"])

    pressure = boundary_pressure(insights)
    if pressure and spotlight["kind"] != pressure["kind"]:
        lines.append(pressure["caption"])

    form = five_round_form(insights)
    if form:
        teams = _join_teams(form["teams"])
        lines.append(f"Em alta: {teams} {'somou' if len(form['teams']) == 1 else 'somaram'} {form['points']} pontos nas últimas 5 rodadas.")

    rise, fall = latest.get("biggest_rise", {}), latest.get("biggest_fall", {})
    if rise.get("places"):
        lines.append(f"Maior subida: {_join_teams(rise.get('teams', []))} (+{rise['places']}).")
    if fall.get("places"):
        lines.append(f"Maior queda: {_join_teams(fall.get('teams', []))} (-{fall['places']}).")

    biggest = latest.get("biggest_win")
    if biggest and biggest.get("winner") != "Empate":
        lines.append(f"Maior vitória: {biggest['winner']} — {biggest['home']} {biggest['score']} {biggest['away']}.")

    lines.extend([
        "",
        f"Mais números e evolução rodada a rodada: {SITE_URL}",
        "",
        "#Brasileirao #Brasileirao2026 #FutebolBrasileiro #SerieA",
    ])
    return "\n".join(lines)[:2200]


def _draw_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font, fill=TEXT, anchor=None) -> None:
    draw.text(xy, text, font=font, fill=fill, anchor=anchor)


def render_card(
    insights: dict,
    output: Path = DEFAULT_OUTPUT,
    now: datetime | None = None,
    matches: list[dict] | None = None,
) -> Path:
    snapshot, latest = current_snapshot(insights)
    table, leader = snapshot["table"], snapshot["table"][0]
    movements = position_movements(insights)
    now = now or datetime.now(TZ)
    image = Image.new("RGB", (1080, 1350), BG)
    draw = ImageDraw.Draw(image)
    title, subtitle, section, body, small, big = _font(50, True), _font(34), _font(34, True), _font(31), _font(25), _font(84, True)

    _draw_text(draw, (70, 70), "BRASILEIRÃO POR RODADAS", title)
    _draw_text(draw, (72, 145), table_hook(insights), subtitle, ACCENT)
    _draw_text(draw, (72, 190), f"Rodada {latest['round']} • {now.strftime('%d/%m/%Y')}", small, MUTED)

    draw.rounded_rectangle((60, 250, 1020, 460), radius=32, fill=PANEL)
    _draw_text(draw, (95, 285), "LÍDER" + (" • RODADA PARCIAL" if latest.get("matches", 10) < 10 else ""), section, ACCENT)
    _draw_text(draw, (95, 340), leader["team"], big)
    _draw_text(draw, (985, 360), f"{leader['points']} pts", section, TEXT, anchor="ra")

    _draw_text(draw, (70, 520), "CLASSIFICAÇÃO", section)
    y = 580
    for row in table[:4]:
        delta = movements.get(row["team"], 0)
        _draw_text(draw, (80, y), f"{row['position']:>2}  {row['team']}", body)
        _draw_text(draw, (840, y), movement_label(delta), small, ACCENT if delta > 0 else RED if delta < 0 else MUTED, anchor="ra")
        _draw_text(draw, (980, y), f"{row['points']} pts", body, anchor="ra")
        y += 58

    _draw_text(draw, (70, 850), "ZONA DE REBAIXAMENTO", section, RED)
    y = 910
    for row in table[-4:]:
        delta = movements.get(row["team"], 0)
        _draw_text(draw, (80, y), f"{row['position']:>2}  {row['team']}", body)
        _draw_text(draw, (840, y), movement_label(delta), small, ACCENT if delta > 0 else RED if delta < 0 else MUTED, anchor="ra")
        _draw_text(draw, (980, y), f"{row['points']} pts", body, anchor="ra")
        y += 58

    spotlight = round_spotlight(insights, matches)
    draw.rounded_rectangle((60, 1165, 1020, 1260), radius=24, fill=PANEL)
    _draw_text(draw, (90, 1185), spotlight["label"], small, ACCENT)
    _draw_text(draw, (90, 1222), spotlight["text"], body)
    _draw_text(draw, (540, 1310), SITE_URL, small, MUTED, anchor="mm")

    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, "PNG", optimize=True)
    return output


def _post(url: str, data: dict, timeout: int = 30) -> dict:
    response = requests.post(url, data=data, timeout=timeout)
    try:
        payload = response.json()
    except ValueError:
        payload = {"raw": response.text}
    if not response.ok:
        raise RuntimeError(f"Instagram API {response.status_code}: {payload}")
    return payload


def publish(image_url: str, caption: str, ig_user_id: str, access_token: str, api_version: str) -> str:
    base = f"{GRAPH_HOST}/{api_version}/{ig_user_id}"
    container = _post(f"{base}/media", {"image_url": image_url, "caption": caption, "access_token": access_token})
    media = _post(f"{base}/media_publish", {"creation_id": container["id"], "access_token": access_token})
    return media["id"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("render", "caption", "publish"))
    parser.add_argument("--insights", type=Path, default=INSIGHTS_FILE)
    parser.add_argument("--matches", type=Path, default=MATCHES_FILE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--image-url")
    args = parser.parse_args()

    insights = load_insights(args.insights)
    matches = load_matches(args.matches)
    caption = build_caption(insights, matches)

    if args.command == "render":
        print(render_card(insights, args.output, matches=matches))
    elif args.command == "caption":
        print(caption)
    else:
        if not args.image_url:
            parser.error("--image-url é obrigatório para publish")
        media_id = publish(
            args.image_url,
            caption,
            os.environ["INSTAGRAM_IG_USER_ID"],
            os.environ["INSTAGRAM_ACCESS_TOKEN"],
            os.getenv("INSTAGRAM_API_VERSION", DEFAULT_API_VERSION),
        )
        print(f"Publicado: {media_id}")


if __name__ == "__main__":
    main()
