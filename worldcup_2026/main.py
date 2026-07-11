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
            rows.append(f'<tr class="stage-header"><td colspan="7">{html.escape(stage)}</td></tr>')
            current_stage = stage

        score = html.escape(match.get("score_display", "-"))
        detail = match.get("score_detail", "")
        if detail:
            score += f'<span class="score-detail">{html.escape(detail)}</span>'

        rows.append(
            "<tr>"
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
<title>Copa do Mundo FIFA 2026</title>
<style>
body{font-family:Arial,sans-serif;margin:20px;background:#fafafa;color:#333}
h1,.subtitle,.footer{text-align:center}table{margin:auto;border-collapse:collapse;width:95%;max-width:1000px;background:#fff}th,td{padding:12px 15px;border:1px solid #ddd;text-align:center}th{background:#1a1a2e;color:#fff}.team{text-align:left;font-weight:bold}.score{font-weight:bold}.score-detail{display:block;font-size:12px;color:#666}.stage-header{background:#e8e8e8;font-weight:bold}.footer{margin-top:30px}
</style>
</head>
<body>
<h1>Copa do Mundo FIFA 2026</h1>
<p class="subtitle">Estados Unidos · México · Canadá | Horários de São Paulo</p>
<table>
<thead><tr><th>Data</th><th>Horário (SP)</th><th>Equipe 1</th><th>Placar</th><th>Equipe 2</th><th>Fase/Grupo</th><th>Estádio</th></tr></thead>
<tbody>
""" + "\n".join(rows) + """
</tbody>
</table>
<p class="footer"><a href="../index.html">← Voltar ao site</a></p>
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
