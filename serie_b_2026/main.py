#!/usr/bin/env python3
"""Atualiza jogos e resultados do Brasileirão Série B 2026 a partir do ge."""

from __future__ import annotations

import html
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

SOURCE_URL = "https://ge.globo.com/futebol/brasileirao-serie-b/"
DATA_FILE = "data/serie_b_2026.json"
OUTPUT_HTML = "docs/serie_b_2026/index.html"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36"


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value)).strip() if value is not None else ""


def fetch_page() -> str:
    local_file = os.getenv("SOURCE_HTML_FILE")
    if local_file:
        return Path(local_file).read_text(encoding="utf-8", errors="replace")
    request = Request(
        SOURCE_URL,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "pt-BR,pt;q=0.9"},
    )
    with urlopen(request, timeout=45) as response:
        return response.read().decode("utf-8", errors="replace")


def balanced_json(text: str, start: int) -> str:
    opening = text[start]
    closing = "}" if opening == "{" else "]"
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise ValueError("JSON embutido no HTML está incompleto")


def extract_js_value(page: str, variable: str) -> Any:
    match = re.search(rf"\b(?:const|let|var)\s+{re.escape(variable)}\s*=\s*", page)
    if not match:
        raise RuntimeError(f"Variável {variable!r} não encontrada no HTML do ge")
    position = match.end()
    while position < len(page) and page[position].isspace():
        position += 1
    if position >= len(page) or page[position] not in "[{":
        raise RuntimeError(f"Valor de {variable!r} não é JSON")
    return json.loads(balanced_json(page, position))


def current_round(page: str) -> int | None:
    match = re.search(r'"rodada"\s*:\s*\{\s*"atual"\s*:\s*(\d+)', page)
    return int(match.group(1)) if match else None


def team_name(team: Any) -> str:
    if not isinstance(team, dict):
        return clean(team)
    return clean(team.get("nome_popular") or team.get("nome") or team.get("sigla"))


def normalize_match(item: dict[str, Any], round_number: int | None) -> dict[str, str]:
    teams = item.get("equipes") or {}
    home = team_name(teams.get("mandante"))
    away = team_name(teams.get("visitante"))
    if not home or not away:
        raise ValueError("Partida sem mandante ou visitante")

    home_score = item.get("placar_oficial_mandante")
    away_score = item.get("placar_oficial_visitante")
    score = (
        f"{home_score} x {away_score}"
        if home_score is not None and away_score is not None
        else "-"
    )

    raw_datetime = clean(item.get("data_realizacao"))
    date = ""
    match_time = clean(item.get("hora_realizacao"))
    if raw_datetime:
        try:
            parsed = datetime.fromisoformat(raw_datetime)
            date = parsed.strftime("%d/%m/%Y")
            match_time = match_time or parsed.strftime("%H:%M")
        except ValueError:
            date = raw_datetime

    venue = item.get("sede") or {}
    transmission = item.get("transmissao") or {}
    return {
        "id": clean(item.get("id")),
        "round": f"{round_number}ª rodada" if round_number else "",
        "date": date,
        "time": match_time,
        "home": home,
        "score": score,
        "away": away,
        "stadium": clean(venue.get("nome_popular") if isinstance(venue, dict) else venue),
        "status": clean(transmission.get("label") if isinstance(transmission, dict) else ""),
        "url": clean(transmission.get("url") if isinstance(transmission, dict) else ""),
    }


def scrape_matches(page: str) -> list[dict[str, str]]:
    raw_matches = extract_js_value(page, "listaJogos")
    if not isinstance(raw_matches, list) or len(raw_matches) < 2:
        raise RuntimeError("O ge não retornou uma rodada válida em listaJogos")
    round_number = current_round(page)
    return [normalize_match(item, round_number) for item in raw_matches]


def load_existing_matches() -> list[dict[str, str]]:
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            matches = json.load(file).get("matches", [])
        return matches if isinstance(matches, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def merge_matches(existing: list[dict[str, str]], scraped: list[dict[str, str]]) -> list[dict[str, str]]:
    merged: dict[str, dict[str, str]] = {}
    for match in existing + scraped:
        key = clean(match.get("id")) or "|".join(
            clean(match.get(field)).casefold()
            for field in ("date", "time", "home", "away")
        )
        if key.strip("|"):
            merged[key] = match

    def sort_key(match: dict[str, str]) -> tuple[str, str, str]:
        try:
            date_key = datetime.strptime(match.get("date", ""), "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            date_key = match.get("date", "")
        return date_key, match.get("time", ""), match.get("home", "")

    return sorted(merged.values(), key=sort_key)


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


def build_html(matches: list[dict[str, str]]) -> str:
    rows = []
    for match in matches:
        score = html.escape(match.get("score", "-"))
        if match.get("url"):
            score = f'<a href="{html.escape(match["url"], quote=True)}">{score}</a>'
        rows.append(
            "<tr>"
            f"<td>{html.escape(match.get('round', ''))}</td>"
            f"<td>{html.escape(match.get('date', ''))}</td>"
            f"<td>{html.escape(match.get('time', ''))}</td>"
            f"<td class=\"team\">{html.escape(match.get('home', ''))}</td>"
            f"<td class=\"score\">{score}</td>"
            f"<td class=\"team\">{html.escape(match.get('away', ''))}</td>"
            f"<td>{html.escape(match.get('stadium', ''))}</td>"
            f"<td>{html.escape(match.get('status', ''))}</td>"
            "</tr>"
        )

    return """<!DOCTYPE html><html lang="pt-br"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Brasileirão Série B 2026</title><style>body{font-family:Arial,sans-serif;margin:20px;background:#fafafa;color:#333}h1,p{text-align:center}table{margin:auto;border-collapse:collapse;width:98%;max-width:1200px;background:white}th,td{padding:10px;border:1px solid #ddd;text-align:center}th{background:#1a1a2e;color:white}.team{text-align:left;font-weight:bold}.score{font-weight:bold}a{color:#007bff;text-decoration:none}</style></head><body><h1>Brasileirão Série B 2026</h1><p>Jogos e resultados obtidos do ge. O histórico é acumulado a cada rodada.</p><table><thead><tr><th>Rodada</th><th>Data</th><th>Hora</th><th>Mandante</th><th>Placar</th><th>Visitante</th><th>Estádio</th><th>Status</th></tr></thead><tbody>""" + "\n".join(rows) + """</tbody></table><p><a href="../index.html">← Voltar ao site</a></p></body></html>\n"""


def main() -> None:
    scraped = scrape_matches(fetch_page())
    matches = merge_matches(load_existing_matches(), scraped)
    data = {"name": "Brasileirão Série B 2026", "source": SOURCE_URL, "matches": matches}
    json_content = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    json_changed = write_if_changed(DATA_FILE, json_content)
    html_changed = write_if_changed(OUTPUT_HTML, build_html(matches))
    print(
        f"{len(scraped)} partidas coletadas; {len(matches)} armazenadas. "
        f"JSON alterado: {json_changed}. HTML alterado: {html_changed}."
    )


if __name__ == "__main__":
    main()
