#!/usr/bin/env python3
"""Atualiza os autores dos gols a partir dos lances estruturados das partidas."""

from __future__ import annotations

import json
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
MATCHES_FILE = ROOT / "data" / "serie_a_2026.json"
OUTPUT_FILE = ROOT / "data" / "serie_a_2026_scorers.json"
USER_AGENT = "Mozilla/5.0 (compatible; Rodada-a-Rodada/1.0; +https://felandim.github.io/)"


def parse_score(value: str) -> tuple[int, int] | None:
    match = re.match(r"^(\d+)\s*x\s*(\d+)", value or "")
    return (int(match.group(1)), int(match.group(2))) if match else None


def decode_property(source: str, name: str, wrapper: str = "") -> Any:
    marker = f"{name}:"
    start = source.find(marker)
    if start < 0:
        raise ValueError(f"Propriedade {name!r} não encontrada")
    value = source[start + len(marker):].lstrip()
    if wrapper:
        if not value.startswith(wrapper):
            raise ValueError(f"Formato inesperado em {name!r}")
        value = value[len(wrapper):]
    return json.JSONDecoder().raw_decode(value)[0]


def download(url: str) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "pt-BR,pt;q=0.9"})
    with urlopen(request, timeout=35) as response:
        return response.read().decode("utf-8", errors="replace")


def aggregate(items: list[tuple[str, bool]]) -> list[dict[str, Any]]:
    counts = Counter(items)
    return [{"name": name, "goals": goals, **({"own_goal": True} if own_goal else {})}
            for (name, own_goal), goals in counts.items()]


def scrape_match(match: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    score = parse_score(match.get("score", ""))
    if not score:
        raise ValueError("Partida ainda não concluída")
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            source = download(match["url"])
            transmission = decode_property(source, "transmission")
            plays = decode_property(source, "plays", "Array.from(")
            home_id = transmission["match"]["homeTeam"]["id"]
            away_id = transmission["match"]["awayTeam"]["id"]
            scorers = {"home": [], "away": []}
            for play in plays:
                if play.get("playType", {}).get("id") != "GOAL":
                    continue
                details = play.get("details") or {}
                athlete = details.get("athlete") or {}
                team_id = (details.get("team") or {}).get("id")
                side = "home" if team_id == home_id else "away" if team_id == away_id else ""
                if not side:
                    continue
                own_goal = details.get("kind") == "OWN_GOAL"
                if own_goal:
                    side = "away" if side == "home" else "home"
                name = athlete.get("popularName") or athlete.get("name") or "Gol contra"
                scorers[side].append((name, own_goal))
            result = {
                "round": match["round"], "score": match["score"],
                "home_team": match["home"], "away_team": match["away"],
                "home": aggregate(scorers["home"]), "away": aggregate(scorers["away"]),
            }
            totals = (sum(item["goals"] for item in result["home"]), sum(item["goals"] for item in result["away"]))
            if totals != score:
                raise ValueError(f"Autores {totals} não conferem com placar {score}")
            return match["url"], result
        except Exception as error:  # noqa: BLE001 - o retry deve cobrir rede e payload
            last_error = error
            time.sleep(attempt + 1)
    raise RuntimeError(f"Falha em {match['home']} x {match['away']}: {last_error}")


def main() -> None:
    matches = json.loads(MATCHES_FILE.read_text(encoding="utf-8"))["matches"]
    completed = [match for match in matches if parse_score(match.get("score", "")) and match.get("url")]
    cache = {"schema_version": 2, "source": "Páginas de partidas do ge", "matches": {}}
    if OUTPUT_FILE.exists():
        cache = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
    cached_matches = cache.setdefault("matches", {})
    rebuild = cache.get("schema_version") != 2
    cache["schema_version"] = 2
    pending = [match for match in completed if rebuild or cached_matches.get(match["url"], {}).get("score") != match["score"]]

    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(scrape_match, match): match for match in pending}
        for index, future in enumerate(as_completed(futures), 1):
            match = futures[future]
            try:
                url, result = future.result()
                cached_matches[url] = result
            except Exception as error:  # noqa: BLE001 - todas as partidas são processadas
                errors.append(str(error))
            if index % 20 == 0 or index == len(pending):
                print(f"Artilheiros: {index}/{len(pending)} partidas processadas")

    cache["matches"] = dict(sorted(cached_matches.items()))
    OUTPUT_FILE.write_text(json.dumps(cache, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    coverage = sum(1 for match in completed if match["url"] in cache["matches"])
    print(f"Cobertura de artilheiros: {coverage}/{len(completed)} partidas concluídas.")
    if errors:
        raise RuntimeError("\n".join(errors))


if __name__ == "__main__":
    main()
