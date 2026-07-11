#!/usr/bin/env python3
"""Atualiza os jogos do Brasileirão Série B 2026 a partir do ge."""

from __future__ import annotations

import html
import json
import os
import re
from datetime import datetime
from typing import Any, Iterable
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup, Tag

SOURCE_URL = "https://ge.globo.com/futebol/brasileirao-serie-b/"
DATA_FILE = "data/serie_b_2026.json"
OUTPUT_HTML = "docs/serie_b_2026/index.html"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


def clean(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def fetch_page() -> str:
    request = Request(
        SOURCE_URL,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "pt-BR,pt;q=0.9",
        },
    )
    with urlopen(request, timeout=45) as response:
        return response.read().decode("utf-8", errors="replace")


def walk_json(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child)


def balanced_json(text: str, start: int) -> str | None:
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
    return None


def script_json_values(soup: BeautifulSoup) -> Iterable[Any]:
    for script in soup.find_all("script"):
        raw = script.string or script.get_text()
        raw = raw.strip()
        if not raw:
            continue

        if raw[0] in "[{":
            try:
                yield json.loads(raw)
                continue
            except json.JSONDecodeError:
                pass

        for match in re.finditer(r"(?:window\.)?__[A-Za-z0-9_]+__\s*=", raw):
            position = match.end()
            while position < len(raw) and raw[position].isspace():
                position += 1
            if position >= len(raw) or raw[position] not in "[{":
                continue
            payload = balanced_json(raw, position)
            if payload:
                try:
                    yield json.loads(payload)
                except json.JSONDecodeError:
                    continue


def pick(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return None


def team_name(value: Any) -> str:
    if isinstance(value, dict):
        return clean(
            pick(
                value,
                "nome_popular",
                "nomePopular",
                "nome",
                "name",
                "sigla",
            )
        )
    return clean(value)


def stadium_name(value: Any) -> str:
    if isinstance(value, dict):
        return clean(pick(value, "nome_popular", "nomePopular", "nome", "name"))
    return clean(value)


def round_name(value: Any) -> str:
    if isinstance(value, dict):
        number = pick(value, "numero", "number", "rodada")
        return f"{clean(number)}ª rodada" if clean(number).isdigit() else clean(number)
    text = clean(value)
    return f"{text}ª rodada" if text.isdigit() else text


def score_values(item: dict[str, Any]) -> tuple[str, str]:
    home = pick(
        item,
        "placar_oficial_mandante",
        "placarOficialMandante",
        "placar_mandante",
        "gols_mandante",
        "home_score",
    )
    away = pick(
        item,
        "placar_oficial_visitante",
        "placarOficialVisitante",
        "placar_visitante",
        "gols_visitante",
        "away_score",
    )

    score = item.get("placar") or item.get("score")
    if isinstance(score, dict):
        home = home if home is not None else pick(score, "mandante", "home", "home_score")
        away = away if away is not None else pick(score, "visitante", "away", "away_score")

    return clean(home), clean(away)


def normalize_json_match(item: dict[str, Any]) -> dict[str, str] | None:
    home_value = pick(item, "mandante", "home", "home_team", "time_mandante")
    away_value = pick(item, "visitante", "away", "away_team", "time_visitante")
    home = team_name(home_value)
    away = team_name(away_value)
    if not home or not away or home == away:
        return None

    home_score, away_score = score_values(item)
    score = f"{home_score} x {away_score}" if home_score != "" and away_score != "" else "-"

    date = clean(pick(item, "data_realizacao", "dataRealizacao", "data", "date"))
    time = clean(pick(item, "hora_realizacao", "horaRealizacao", "hora", "time"))
    stadium = stadium_name(pick(item, "estadio", "stadium", "local"))
    round_value = pick(item, "rodada", "round", "numero_rodada", "numeroRodada")
    identifier = clean(pick(item, "id", "jogo_id", "jogoId", "slug"))

    if "T" in date:
        try:
            parsed = datetime.fromisoformat(date.replace("Z", "+00:00"))
            if not time:
                time = parsed.strftime("%H:%M")
            date = parsed.strftime("%d/%m/%Y")
        except ValueError:
            pass

    return {
        "id": identifier,
        "round": round_name(round_value),
        "date": date,
        "time": time,
        "home": home,
        "score": score,
        "away": away,
        "stadium": stadium,
    }


def text_from(node: Tag, selectors: list[str]) -> str:
    for selector in selectors:
        found = node.select_one(selector)
        if found:
            value = clean(found.get_text(" ", strip=True))
            if value:
                return value
    return ""


def parse_dom_matches(soup: BeautifulSoup) -> list[dict[str, str]]:
    matches: list[dict[str, str]] = []
    selectors = [
        ".lista-jogos__jogo",
        "[class*='lista-jogos'][class*='jogo']",
        "article[class*='jogo']",
    ]
    nodes: list[Tag] = []
    for selector in selectors:
        nodes.extend(soup.select(selector))

    for node in nodes:
        team_nodes = node.select(".equipes__nome, [class*='equipe'][class*='nome']")
        teams = [clean(team.get_text(" ", strip=True)) for team in team_nodes]
        teams = [team for team in teams if team]
        if len(teams) < 2:
            continue

        scores = [
            clean(value.get_text(" ", strip=True))
            for value in node.select(".placar-box, [class*='placar'][class*='valor']")
        ]
        scores = [value for value in scores if re.fullmatch(r"\d+", value)]
        score = f"{scores[0]} x {scores[1]}" if len(scores) >= 2 else "-"

        matches.append(
            {
                "id": clean(node.get("data-id", "")),
                "round": text_from(node, ["[class*='rodada']"]),
                "date": text_from(node, ["[class*='data']"]),
                "time": text_from(node, ["[class*='hora']"]),
                "home": teams[0],
                "score": score,
                "away": teams[1],
                "stadium": text_from(node, ["[class*='estadio']", "[class*='local']"]),
            }
        )
    return matches


def deduplicate(matches: list[dict[str, str]]) -> list[dict[str, str]]:
    unique: dict[str, dict[str, str]] = {}
    for match in matches:
        key = match.get("id") or "|".join(
            clean(match.get(field, "")).casefold()
            for field in ("date", "time", "home", "away")
        )
        if not key.strip("|"):
            continue
        current = unique.get(key)
        if current is None or current.get("score") == "-":
            unique[key] = match

    return sorted(
        unique.values(),
        key=lambda match: (
            clean(match.get("date")),
            clean(match.get("time")),
            clean(match.get("home")),
        ),
    )


def parse_matches(page: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(page, "lxml")
    matches: list[dict[str, str]] = []

    for payload in script_json_values(soup):
        for item in walk_json(payload):
            match = normalize_json_match(item)
            if match:
                matches.append(match)

    matches.extend(parse_dom_matches(soup))
    matches = deduplicate(matches)
    if not matches:
        raise RuntimeError(
            "Nenhuma partida foi encontrada no ge. O HTML pode ter mudado; "
            "os arquivos existentes foram preservados."
        )
    return matches


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
        rows.append(
            "<tr>"
            f"<td>{html.escape(match['round'])}</td>"
            f"<td>{html.escape(match['date'])}</td>"
            f"<td>{html.escape(match['time'])}</td>"
            f"<td class=\"team\">{html.escape(match['home'])}</td>"
            f"<td class=\"score\">{html.escape(match['score'])}</td>"
            f"<td class=\"team\">{html.escape(match['away'])}</td>"
            f"<td>{html.escape(match['stadium'])}</td>"
            "</tr>"
        )

    return """<!DOCTYPE html><html lang="pt-br"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Brasileirão Série B 2026</title><style>body{font-family:Arial,sans-serif;margin:20px;background:#fafafa;color:#333}h1,p{text-align:center}table{margin:auto;border-collapse:collapse;width:95%;max-width:1100px;background:white}th,td{padding:10px;border:1px solid #ddd;text-align:center}th{background:#1a1a2e;color:white}.team{text-align:left;font-weight:bold}.score{font-weight:bold}</style></head><body><h1>Brasileirão Série B 2026</h1><p>Jogos e resultados obtidos do ge</p><table><thead><tr><th>Rodada</th><th>Data</th><th>Hora</th><th>Mandante</th><th>Placar</th><th>Visitante</th><th>Estádio</th></tr></thead><tbody>""" + "\n".join(rows) + """</tbody></table><p><a href="../index.html">← Voltar ao site</a></p></body></html>\n"""


def main() -> None:
    matches = parse_matches(fetch_page())
    data = {
        "name": "Brasileirão Série B 2026",
        "source": SOURCE_URL,
        "matches": matches,
    }
    json_content = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    json_changed = write_if_changed(DATA_FILE, json_content)
    html_changed = write_if_changed(OUTPUT_HTML, build_html(matches))
    print(
        f"{len(matches)} partidas encontradas. "
        f"JSON alterado: {json_changed}. HTML alterado: {html_changed}."
    )


if __name__ == "__main__":
    main()
