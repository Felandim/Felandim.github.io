#!/usr/bin/env python3
"""Atualiza jogos da Série B 2026 a partir das tabelas públicas da Wikipédia."""

import html
import json
import os
import re
from datetime import datetime

import pandas as pd

SOURCE_URL = "https://es.wikipedia.org/wiki/Campeonato_Brasile%C3%B1o_de_F%C3%BAtbol_Serie_B_2026"
DATA_FILE = "data/serie_b_2026.json"
OUTPUT_HTML = "docs/serie_b_2026/index.html"


def clean(value) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


def parse_tables() -> list[dict]:
    matches = []
    tables = pd.read_html(SOURCE_URL)

    for table in tables:
        table.columns = [clean(col).lower() for col in table.columns]
        required = {"local", "resultado", "visitante"}
        if not required.issubset(table.columns):
            continue

        table = table.ffill()
        for _, row in table.iterrows():
            score = clean(row.get("resultado", ""))
            if not re.search(r"\d+\s*[–x-]\s*\d+", score):
                continue

            matches.append({
                "home": clean(row.get("local", "")),
                "score": score.replace("–", "x").replace("-", "x"),
                "away": clean(row.get("visitante", "")),
                "date": clean(row.get("fecha", "")),
                "time": clean(row.get("hora", "")),
                "stadium": clean(row.get("estadio", "")),
            })

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


def build_html(matches: list[dict]) -> str:
    rows = []
    for match in matches:
        rows.append(
            "<tr>"
            f"<td>{html.escape(match['date'])}</td>"
            f"<td>{html.escape(match['time'])}</td>"
            f"<td class=\"team\">{html.escape(match['home'])}</td>"
            f"<td class=\"score\">{html.escape(match['score'])}</td>"
            f"<td class=\"team\">{html.escape(match['away'])}</td>"
            f"<td>{html.escape(match['stadium'])}</td>"
            "</tr>"
        )

    return """<!DOCTYPE html><html lang="pt-br"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Brasileirão Série B 2026</title><style>body{font-family:Arial,sans-serif;margin:20px;background:#fafafa;color:#333}h1,p{text-align:center}table{margin:auto;border-collapse:collapse;width:95%;max-width:1000px;background:white}th,td{padding:10px;border:1px solid #ddd;text-align:center}th{background:#1a1a2e;color:white}.team{text-align:left;font-weight:bold}.score{font-weight:bold}</style></head><body><h1>Brasileirão Série B 2026</h1><p>Resultados atualizados automaticamente</p><table><thead><tr><th>Data</th><th>Hora</th><th>Mandante</th><th>Placar</th><th>Visitante</th><th>Estádio</th></tr></thead><tbody>""" + "\n".join(rows) + """</tbody></table><p><a href="../index.html">← Voltar ao site</a></p></body></html>\n"""


def main() -> None:
    matches = parse_tables()
    data = {
        "name": "Brasileirão Série B 2026",
        "source": SOURCE_URL,
        "matches": matches,
    }
    json_content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    json_changed = write_if_changed(DATA_FILE, json_content)
    html_changed = write_if_changed(OUTPUT_HTML, build_html(matches))
    print(f"{len(matches)} partidas encontradas. JSON alterado: {json_changed}. HTML alterado: {html_changed}.")


if __name__ == "__main__":
    main()
