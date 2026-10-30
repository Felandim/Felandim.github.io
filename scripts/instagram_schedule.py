#!/usr/bin/env python3
"""Publica cada bloco da mesma rodada no dia seguinte ao seu encerramento."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import defaultdict
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
TZ = ZoneInfo("America/Sao_Paulo")
GAP = timedelta(hours=48)
STATE = ROOT / "data/instagram_blocks_published.json"
CARDS = ROOT / "assets/instagram/blocks"


def completed(match: dict) -> bool:
    return bool(re.fullmatch(r"\d+\s*x\s*\d+", str(match.get("score") or "").strip()))


def kickoff_window(match: dict) -> tuple[datetime, datetime] | None:
    # Adiamentos sem nova data ficam fora do bloco; um novo horário válido os reinsere.
    try:
        day = datetime.strptime(match.get("date", ""), "%d/%m/%Y").date()
    except (ValueError, TypeError):
        return None
    status = str(match.get("status") or "").lower()
    if not completed(match) and status in {"adiado", "postponed", "cancelado", "cancelled", "suspended", "suspenso"}:
        return None
    try:
        clock = datetime.strptime(match.get("time", ""), "%H:%M").time()
    except (ValueError, TypeError):
        # Sem horário, só separamos quando até o menor intervalo possível supera 48h.
        return datetime.combine(day, time.min, TZ), datetime.combine(day, time.max, TZ)
    instant = datetime.combine(day, clock, TZ)
    return instant, instant


def match_key(match: dict) -> str:
    return json.dumps([match["round"], match["home"], match["away"]], ensure_ascii=False)


def round_blocks(matches: list[dict]) -> list[dict]:
    rounds = defaultdict(list)
    for match in matches:
        window = kickoff_window(match)
        if window is not None:
            rounds[int(match["round"])].append((window, match))
    blocks = []
    for round_number, fixtures in sorted(rounds.items()):
        current = None
        for (start, end), match in sorted(fixtures, key=lambda item: item[0][0]):
            if current is None or start - current["end"] > GAP:
                current = {"round": round_number, "start": start, "end": end, "matches": []}
                blocks.append(current)
            current["end"] = max(current["end"], end)
            current["matches"].append(match)
    return blocks


def due_blocks(matches: list[dict], now: datetime | None = None, state: dict | None = None) -> list[dict]:
    now = (now or datetime.now(TZ)).astimezone(TZ)
    if now.hour < 10:
        return []
    yesterday = now.date() - timedelta(days=1)
    recorded = {key for entry in (state or {}).values() for key in entry.get("match_keys", [])}
    due = []
    for block in round_blocks(matches):
        if block["end"].date() != yesterday or not all(completed(m) for m in block["matches"]):
            continue
        selected = [m for m in block["matches"] if match_key(m) not in recorded]
        if not selected:
            continue
        keys = sorted(match_key(m) for m in selected)
        block_id = hashlib.sha256("\n".join(keys).encode()).hexdigest()[:20]
        due.append({"id": block_id, "round": block["round"], "start": block["start"].date().isoformat(),
                    "end": block["end"].date().isoformat(), "matches": selected, "match_keys": keys})
    return due


def block_spotlight(insights: dict, block: dict, scorer_data: dict | None = None) -> dict:
    import instagram_editorial
    matches = block["matches"]
    scorer = instagram_editorial.multi_goal_scorer_spotlight(matches, scorer_data)
    collective = instagram_editorial.collective_attack_spotlight(matches, scorer_data)
    bounce_back = instagram_editorial.bounce_back_spotlight(insights, matches)
    drought_end = instagram_editorial.winless_run_ended_spotlight(insights, matches)
    unbeaten_run = instagram_editorial.unbeaten_run_spotlight(insights, matches)
    if len(matches) == 1:
        if scorer:
            return scorer
        if collective:
            return collective
        if bounce_back:
            return bounce_back
        if drought_end:
            return drought_end
        if unbeaten_run:
            return unbeaten_run
        # Pontos deste jogo e posição atual, sem atribuir movimentos de outros jogos a ele.
        match = matches[0]
        home, away = (int(n) for n in re.split(r"\s*x\s*", match["score"].strip()))
        points = (3, 0) if home > away else (0, 3) if away > home else (1, 1)
        table = {row["team"]: row for row in insights["snapshots"][-1]["table"]}
        impact = []
        for team, gained in zip((match["home"], match["away"]), points):
            row = table.get(team)
            detail = f"{team}: +{gained} {'ponto' if gained == 1 else 'pontos'}"
            if row:
                detail += f"; agora {row['points']} pontos, {row['position']}º lugar"
            impact.append(detail + ".")
        score = f"{match['home']} {match['score']} {match['away']}"
        return {"kind": "isolated_match", "label": "IMPACTO NA TABELA",
                "text": f"{score} • {block['round']}ª rodada",
                "caption": f"{score}, pela {block['round']}ª rodada. " + " ".join(impact)}
    spotlight = dict(instagram_editorial.editorial_spotlight(insights, matches, scorer_data))
    for field in ("label", "text", "caption"):
        if field in spotlight:
            spotlight[field] = (spotlight[field].replace("do dia", "do bloco")
                                .replace("DIA SEM", "BLOCO SEM").replace("Dia sem", "Bloco sem"))
    return spotlight


def prepare_content(insights: dict, block: dict, output: Path) -> str:
    from PIL import Image
    import instagram_daily
    import instagram_editorial
    import instagram_engagement
    import instagram_matchday
    scorer_data = instagram_daily.load_scorers()
    spotlight = block_spotlight(insights, block, scorer_data)
    instagram_editorial.render_card(insights, block["matches"], output, scorer_data=scorer_data)
    with Image.open(output) as source:
        image = source.convert("RGB")
    instagram_matchday.draw_spotlight(image, spotlight)
    image.save(output, "PNG", optimize=True)
    base = instagram_editorial.build_caption(insights, block["matches"], scorer_data)
    lines = base.splitlines()
    lines[0] = instagram_editorial._spotlight_sentence(spotlight)
    start = datetime.fromisoformat(block["start"]).strftime("%d/%m")
    end = datetime.fromisoformat(block["end"]).strftime("%d/%m")
    period = end if start == end else f"{start} a {end}"
    lines[1] = f"Brasileirão {insights['season']} — bloco da {block['round']}ª rodada ({period})."
    caption = instagram_engagement.with_engagement_question("\n".join(lines), spotlight)
    return caption


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_state(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def publish_plan(plan: list[dict], image_base_url: str, state_path: Path = STATE) -> None:
    import instagram_daily
    import instagram_engagement
    state = read_state(state_path)
    for block in plan:
        if block["id"] in state:
            continue
        # Persiste a tentativa mesmo em erro ambíguo, para não repetir um POST de publicação.
        state[block["id"]] = {"outcome": "started", "match_keys": block["match_keys"]}
        write_json(state_path, state)
        media_id = instagram_engagement.publish_when_ready(
            instagram_daily, f"{image_base_url.rstrip('/')}/{block['id']}.png", block["caption"],
            os.environ["INSTAGRAM_IG_USER_ID"], os.environ["INSTAGRAM_ACCESS_TOKEN"],
            os.getenv("INSTAGRAM_API_VERSION", instagram_daily.DEFAULT_API_VERSION),
        )
        state[block["id"]].update(outcome="published", media_id=media_id,
                                  published_at=datetime.now(TZ).isoformat())
        write_json(state_path, state)
        print(f"Bloco {block['id']} publicado: {media_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("select", "render", "publish"))
    parser.add_argument("--plan", type=Path, default=Path("/tmp/instagram-plan.json"))
    parser.add_argument("--matches", type=Path, default=ROOT / "data/serie_a_2026.json")
    parser.add_argument("--state", type=Path, default=STATE)
    parser.add_argument("--image-base-url")
    args = parser.parse_args()
    if args.command == "select":
        matches = json.loads(args.matches.read_text(encoding="utf-8"))["matches"]
        plan = due_blocks(matches, state=read_state(args.state))
        write_json(args.plan, plan)
        print(f"{len(plan)} bloco(s) encerrado(s) com publicação devida.")
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
                out.write(f"publish={'true' if plan else 'false'}\n")
    elif args.command == "render":
        import instagram_daily
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
        insights = instagram_daily.load_insights()
        CARDS.mkdir(parents=True, exist_ok=True)
        for block in plan:
            block["caption"] = prepare_content(insights, block, CARDS / f"{block['id']}.png")
        write_json(args.plan, plan)
    else:
        if not args.image_base_url:
            parser.error("publish exige --image-base-url")
        publish_plan(json.loads(args.plan.read_text(encoding="utf-8")), args.image_base_url, args.state)


if __name__ == "__main__":
    main()
