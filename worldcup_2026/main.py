#!/usr/bin/env python3
"""Atualiza os jogos da Copa do Mundo FIFA 2026 e gera uma página estática."""

import html
import json
import os
import re
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

SOURCE_URL = "https://raw.githubusercontent.com/upbound-web/worldcup-live.json/master/2026/worldcup.json"
DATA_FILE = "data/worldcup_2026.json"
OUTPUT_HTML = "docs/worldcup_2026/index.html"
TIMEZONE_SP = ZoneInfo("America/Sao_Paulo")


def download_json(url: str) -> dict:
    req = Request(url, headers={"User-Agent": "Felandim.github.io updater"})
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_utc_offset(time_str: str) -> int:
    match = re.search(r"UTC([+-]\d{1,2})", time_str)
    return int(match.group(1)) if match else 0


def convert_to_sao_paulo(date_str: str, time_str: str) -> tuple[str, str]:
    time_part = time_str.split()[0]
    hour, minute = map(int, time_part.split(":"))
    utc_offset = parse_utc_offset(time_str)

    source_tz = timezone(timedelta(hours=utc_offset))
    source_dt = datetime.strptime(date_str, "%Y-%m-%d").replace(
        hour=hour,
        minute=minute,
        tzinfo=source_tz,
    )
    sp_dt = source_dt.astimezone(TIMEZONE_SP)
    return sp_dt.strftime("%Y-%m-%d"), sp_dt.strftime("%H:%M")


def format_score(score: dict) -> tuple[str, str]:
    ft = score.get("ft", [])
    if len(ft) != 2:
        return "-", ""

    main = f"{ft[0]} x {ft[1]}"
    details = []

    et = score.get("et", [])
    if len(et) == 2 and et != ft:
        details.append(f"PR: {et[0]}x{et[1]}")

    penalties = score.get("p", [])
    if len(penalties) == 2:
        details.append(f"PEN: {penalties[0]}x{penalties[1]}")

    return main, " | ".join(details)


def determine_stage(match: dict) -> str:
    if match.get("group"):
        return match["group"]

    round_name = match.get("round", "")
    normalized = round_name.lower()
    if "round of 32" in normalized:
        return "Round of 32"
    if "round of 16" in normalized:
        return "Round of 16"
    if "quarter" in normalized:
        return "Quarterfinals"
    if "semi" in normalized:
        return "Semifinals"
    if "third" in normalized:
        return "Third Place"
    if "final" in normalized:
        return "Final"
    return round_name


def process_data(source: dict) -> dict:
    processed_matches = []

    for original in source.get("matches", []):
        match = dict(original)
        try:
            date_sp, time_sp = convert_to_sao_paulo(
                match.get("date", ""),
                match.get("time", ""),
            )
        except (ValueError, IndexError):
            date_sp = match.get("date", "")
            time_sp = match.get("time", "").split()[0] if match.get("time") else "-"

        score_main, score_detail = format_score(match.get("score", {}))
        match["date_sp"] = date_sp
        match["time_sp"] = time_sp
        match["score_display"] = score_main
        match["score_detail"] = score_detail
        match["stage"] = determine_stage(match)
        processed_matches.append(match)

    processed_matches.sort(key=lambda item: (item.get("date_sp", ""), item.get("time_sp", "")))

    return {
        "name": source.get("name", "World Cup 2026"),
        "source": SOURCE_URL,
        "matches": processed_matches,
    }


def write_json_if_changed(data: dict) -> bool:
    existing = None
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            existing = json.load(file)

    if existing == data:
        print("JSON inalterado.")
        return False

    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")

    print(f"JSON salvo em {DATA_FILE}.")
    return True


def format_date_br(value: str) -> str:
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return value


def generate_html(data: dict) -> str:
    rows = []
    current_stage = None

    for match in data.get("matches", []):
        stage = match.get("stage", "")
        if stage != current_stage:
            rows.append(f'<tr class="group-row"><td colspan="7">{html.escape(stage)}</td></tr>')
            current_stage = stage

        score = html.escape(match.get("score_display", "-"))
        detail = match.get("score_detail", "")
        if detail:
            score += f'<span class="score-detail">{html.escape(detail)}</span>'

        rows.append(
            "<tr data-match-row>"
            f"<td>{html.escape(format_date_br(match.get('date_sp', '')))}</td>"
            f"<td>{html.escape(match.get('time_sp', '-'))}</td>"
            f"<td class=\"team\">{html.escape(match.get('team1', '-'))}</td>"
            f"<td class=\"score\">{score}</td>"
            f"<td class=\"team\">{html.escape(match.get('team2', '-'))}</td>"
            f"<td>{html.escape(stage)}</td>"
            f"<td>{html.escape(match.get('ground', '-'))}</td>"
            "</tr>"
        )

    return """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Jogos da Copa do Mundo 2026: horários e resultados</title>
<meta name="description" content="Consulte os 104 jogos da Copa do Mundo 2026, com horários de São Paulo, grupos, resultados e estádios. Dados atualizados automaticamente.">
<link rel="canonical" href="https://felandim.github.io/docs/worldcup_2026/">
<link rel="stylesheet" href="../../style.css">
</head>
<body class="football-page">
<header class="site-header"><div class="container nav-wrap"><a class="brand" href="../../index.html"><span>FL</span> Felipe Landim</a><nav class="site-nav" aria-label="Navegação principal"><a href="../../projetos.html">Projetos</a><a href="../../dados-futebol.html" aria-current="page">Dados de futebol</a><a href="../../artigos.html">Artigos</a><a href="../../about.html">Sobre</a></nav></div></header>
<main>
<section class="football-header"><div class="container football-intro"><div class="breadcrumb"><a href="../../index.html">Início</a><span>/</span><a href="../../dados-futebol.html">Dados de futebol</a><span>/</span><span>Copa 2026</span></div><p class="eyebrow">Atualização automática a cada 4 horas</p><h1>Jogos da Copa do Mundo 2026</h1><p>Estados Unidos · México · Canadá · Horários convertidos para São Paulo</p><a class="button button-primary story-inline-cta" href="../../gerador-card-futebol.html?campeonato=worldcup">Criar card para Stories →</a></div></section>
<section class="container">
<div class="football-toolbar"><div class="search-field"><label for="match-search">Buscar seleção, estádio ou fase</label><input id="match-search" type="search" placeholder="Ex.: Brasil, Miami ou Grupo C" data-match-search autocomplete="off"></div><div class="result-count" data-result-count aria-live="polite"></div></div>
<aside class="ad-slot" data-ad-slot="football-top" hidden aria-label="Publicidade"></aside>
<div class="table-shell"><div class="table-scroll"><table class="data-table">
<thead><tr><th scope="col">Data</th><th scope="col">Horário (SP)</th><th scope="col">Equipe 1</th><th scope="col">Placar</th><th scope="col">Equipe 2</th><th scope="col">Fase/Grupo</th><th scope="col">Estádio</th></tr></thead>
<tbody>
""" + "\n".join(rows) + """
</tbody>
</table></div><div class="source-note">Dados de origem: <a href="https://github.com/upbound-web/worldcup-live.json">upbound-web/worldcup-live.json</a>. Horários tratados para o fuso de São Paulo. <a href="../../dados-futebol.html">Entenda o pipeline.</a></div></div>
</section></main>
<footer class="site-footer"><div class="container footer-bottom"><span>© Felipe Landim</span><a href="../../dados-futebol.html">Mais dados de futebol</a></div></footer>
<script src="../../football.js" defer></script>
</body>
</html>
"""


def write_html_if_changed(content: str) -> bool:
    existing = None
    if os.path.exists(OUTPUT_HTML):
        with open(OUTPUT_HTML, "r", encoding="utf-8") as file:
            existing = file.read()

    if existing == content:
        print("HTML inalterado.")
        return False

    os.makedirs(os.path.dirname(OUTPUT_HTML), exist_ok=True)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as file:
        file.write(content)

    print(f"HTML salvo em {OUTPUT_HTML}.")
    return True


def main() -> None:
    source = download_json(SOURCE_URL)
    data = process_data(source)

    json_changed = write_json_if_changed(data)
    html_changed = write_html_if_changed(generate_html(data))

    if not json_changed and not html_changed:
        print("Nenhuma alteração detectada.")


if __name__ == "__main__":
    main()
