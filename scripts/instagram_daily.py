#!/usr/bin/env python3
"""Gera e publica o resumo diário do Brasileirão por Rodadas no Instagram."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
INSIGHTS_FILE = ROOT / "data" / "brasileirao_2026_insights.json"
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
    paths = [
        Path("/usr/share/fonts/truetype/dejavu") / name,
        Path("/usr/share/fonts/dejavu") / name,
    ]
    for path in paths:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def load_insights(path: Path = INSIGHTS_FILE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def current_snapshot(insights: dict) -> tuple[dict, dict]:
    if not insights.get("snapshots") or not insights.get("rounds"):
        raise ValueError("Insights sem rodadas concluídas.")
    return insights["snapshots"][-1], insights["rounds"][-1]


def _join_teams(values: list[str], empty: str = "ninguém") -> str:
    return ", ".join(values) if values else empty


def five_round_form(insights: dict) -> dict | None:
    """Retorna quem mais pontuou entre o snapshot atual e o de cinco rodadas atrás."""
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


def table_hook(insights: dict) -> str:
    """Cria um gancho factual curto a partir da disputa por título ou contra o Z4."""
    snapshot, _ = current_snapshot(insights)
    table = snapshot["table"]
    if len(table) < 17:
        return "A tabela segue em movimento"

    title_gap = table[0]["points"] - table[1]["points"]
    relegation_gap = table[15]["points"] - table[16]["points"]

    if title_gap <= 3:
        unit = "ponto" if title_gap == 1 else "pontos"
        return f"Liderança separada por {title_gap} {unit}"
    if relegation_gap <= 3:
        unit = "ponto" if relegation_gap == 1 else "pontos"
        return f"Fora do Z4 por apenas {relegation_gap} {unit}"

    return f"Líder abre {title_gap} pontos na ponta"


def build_caption(insights: dict) -> str:
    snapshot, latest = current_snapshot(insights)
    table = snapshot["table"]
    leader = table[0]
    top4 = ", ".join(row["team"] for row in table[:4])
    z4 = ", ".join(row["team"] for row in table[-4:])

    lines = [
        table_hook(insights) + ".",
        f"Brasileirão {insights['season']} — rodada {latest['round']}" + (" (parcial)." if latest.get('matches', 10) < 10 else "."),
        "",
        f"Líder: {leader['team']} — {leader['points']} pts.",
        f"G4: {top4}.",
        f"Z4: {z4}.",
        f"Gols na rodada: {latest['goals']}.",
    ]

    form = five_round_form(insights)
    if form:
        teams = _join_teams(form["teams"])
        verb = "somou" if len(form["teams"]) == 1 else "somaram"
        lines.append(f"Em alta: {teams} {verb} {form['points']} pontos nas últimas 5 rodadas.")

    rise = latest.get("biggest_rise", {})
    fall = latest.get("biggest_fall", {})
    if rise.get("places"):
        lines.append(f"Maior subida: {_join_teams(rise.get('teams', []))} (+{rise['places']}).")
    if fall.get("places"):
        lines.append(f"Maior queda: {_join_teams(fall.get('teams', []))} (-{fall['places']}).")

    biggest = latest.get("biggest_win")
    if biggest and biggest.get("winner") != "Empate":
        lines.append(
            f"Maior vitória: {biggest['winner']} — {biggest['home']} {biggest['score']} {biggest['away']}."
        )

    lines.extend([
        "",
        f"Mais números e evolução rodada a rodada: {SITE_URL}",
        "",
        "#Brasileirao #Brasileirao2026 #FutebolBrasileiro #SerieA",
    ])
    return "\n".join(lines)[:2200]


def _draw_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font, fill=TEXT, anchor=None) -> None:
    draw.text(xy, text, font=font, fill=fill, anchor=anchor)


def render_card(insights: dict, output: Path = DEFAULT_OUTPUT, now: datetime | None = None) -> Path:
    snapshot, latest = current_snapshot(insights)
    table = snapshot["table"]
    leader = table[0]
    now = now or datetime.now(TZ)

    image = Image.new("RGB", (1080, 1350), BG)
    draw = ImageDraw.Draw(image)

    title = _font(50, True)
    subtitle = _font(34)
    section = _font(34, True)
    body = _font(31)
    small = _font(25)
    big = _font(84, True)

    _draw_text(draw, (70, 70), "BRASILEIRÃO POR RODADAS", title)
    _draw_text(draw, (72, 145), table_hook(insights), subtitle, ACCENT)
    _draw_text(draw, (72, 190), f"Rodada {latest['round']} • {now.strftime('%d/%m/%Y')}", small, MUTED)

    draw.rounded_rectangle((60, 250, 1020, 460), radius=32, fill=PANEL)
    round_label = f"LÍDER" + (" • RODADA PARCIAL" if latest.get('matches', 10) < 10 else "")
    _draw_text(draw, (95, 285), round_label, section, ACCENT)
    _draw_text(draw, (95, 340), leader["team"], big)
    _draw_text(draw, (985, 360), f"{leader['points']} pts", section, TEXT, anchor="ra")

    _draw_text(draw, (70, 520), "CLASSIFICAÇÃO", section)
    y = 580
    for row in table[:4]:
        _draw_text(draw, (80, y), f"{row['position']:>2}  {row['team']}", body)
        _draw_text(draw, (980, y), f"{row['points']} pts", body, anchor="ra")
        y += 58

    _draw_text(draw, (70, 850), "ZONA DE REBAIXAMENTO", section, RED)
    y = 910
    for row in table[-4:]:
        _draw_text(draw, (80, y), f"{row['position']:>2}  {row['team']}", body)
        _draw_text(draw, (980, y), f"{row['points']} pts", body, anchor="ra")
        y += 58

    form = five_round_form(insights)
    draw.rounded_rectangle((60, 1165, 1020, 1260), radius=24, fill=PANEL)
    if form:
        teams = _join_teams(form["teams"][:2])
        if len(form["teams"]) > 2:
            teams += " + outros"
        _draw_text(draw, (90, 1185), "EM ALTA • ÚLTIMAS 5 RODADAS", small, ACCENT)
        _draw_text(draw, (90, 1222), f"{teams} • {form['points']} pontos", body)
    else:
        _draw_text(draw, (90, 1198), f"{latest['goals']} gols na rodada", small)

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
    container = _post(
        f"{base}/media",
        {"image_url": image_url, "caption": caption, "access_token": access_token},
    )
    creation_id = container["id"]
    media = _post(
        f"{base}/media_publish",
        {"creation_id": creation_id, "access_token": access_token},
    )
    return media["id"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("render", "caption", "publish"))
    parser.add_argument("--insights", type=Path, default=INSIGHTS_FILE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--image-url")
    args = parser.parse_args()

    insights = load_insights(args.insights)
    caption = build_caption(insights)

    if args.command == "render":
        path = render_card(insights, args.output)
        print(path)
    elif args.command == "caption":
        print(caption)
    else:
        if not args.image_url:
            parser.error("--image-url é obrigatório para publish")
        ig_user_id = os.environ["INSTAGRAM_IG_USER_ID"]
        access_token = os.environ["INSTAGRAM_ACCESS_TOKEN"]
        api_version = os.getenv("INSTAGRAM_API_VERSION", DEFAULT_API_VERSION)
        media_id = publish(args.image_url, caption, ig_user_id, access_token, api_version)
        print(f"Publicado: {media_id}")


if __name__ == "__main__":
    main()
