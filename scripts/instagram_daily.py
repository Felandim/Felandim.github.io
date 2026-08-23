#!/usr/bin/env python3
"""Gera e publica o resumo diário do Brasileirão por Rodadas no Instagram."""

from __future__ import annotations

import argparse
import json
import os
import textwrap
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


def build_caption(insights: dict) -> str:
    snapshot, latest = current_snapshot(insights)
    table = snapshot["table"]
    leader = table[0]
    top4 = ", ".join(row["team"] for row in table[:4])
    z4 = ", ".join(row["team"] for row in table[-4:])

    lines = [
        f"Brasileirão {insights['season']} — resumo da rodada {latest['round']}" + (" (parcial)." if latest.get('matches', 10) < 10 else "."),
        "",
        f"Líder: {leader['team']} — {leader['points']} pts.",
        f"G4: {top4}.",
        f"Z4: {z4}.",
        f"Gols na rodada: {latest['goals']}.",
    ]

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
    _draw_text(draw, (72, 157), f"Resumo diário • {now.strftime('%d/%m/%Y')}", subtitle, MUTED)

    draw.rounded_rectangle((60, 230, 1020, 450), radius=32, fill=PANEL)
    round_label = f"RODADA {latest['round']}" + (" • PARCIAL" if latest.get('matches', 10) < 10 else "")
    _draw_text(draw, (95, 270), round_label, section, ACCENT)
    _draw_text(draw, (95, 330), leader["team"], big)
    _draw_text(draw, (985, 350), f"{leader['points']} pts", section, TEXT, anchor="ra")

    _draw_text(draw, (70, 515), "CLASSIFICAÇÃO", section)
    y = 575
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

    rise = latest.get("biggest_rise", {})
    fall = latest.get("biggest_fall", {})
    insights_line = []
    if rise.get("places"):
        insights_line.append(f"↑ {_join_teams(rise.get('teams', []))} +{rise['places']}")
    if fall.get("places"):
        insights_line.append(f"↓ {_join_teams(fall.get('teams', []))} -{fall['places']}")
    movement = "   •   ".join(insights_line) or "Sem grandes mudanças de posição"
    movement = textwrap.shorten(movement, width=62, placeholder="…")

    draw.rounded_rectangle((60, 1165, 1020, 1260), radius=24, fill=PANEL)
    _draw_text(draw, (90, 1198), f"{latest['goals']} gols na rodada   •   {movement}", small)
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
