#!/usr/bin/env python3
"""
Script para baixar e processar dados da Copa do Mundo FIFA 2026.
Fonte: upbound-web/worldcup-live.json
"""

import json
import re
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import urlopen, Request
from zoneinfo import ZoneInfo

SOURCE_URL = "https://raw.githubusercontent.com/upbound-web/worldcup-live.json/master/2026/worldcup.json"
DATA_FILE = "data/worldcup_2026.json"
OUTPUT_DIR = "docs/worldcup_2026"
OUTPUT_HTML = "docs/worldcup_2026/index.html"
TIMEZONE_SP = ZoneInfo("America/Sao_Paulo")


def download_json(url: str) -> dict:
    """Baixa o JSON da fonte."""
    print(f"Baixando dados de: {url}")
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_utc_offset(time_str: str) -> int:
    """Extrai o offset UTC da string de horário."""
    match = re.search(r"UTC([+-]\d+)", time_str)
    if match:
        return int(match.group(1))
    return 0


def convert_to_sao_paulo(date_str: str, time_str: str, utc_offset: int) -> tuple[str, str]:
    """Converte data/hora para o fuso de São Paulo usando timezone-aware datetime."""
    try:
        time_part = time_str.split()[0]
        hour, minute = map(int, time_part.split(":"))
        
        # Criar datetime consciente do fuso local do jogo
        local_tz = timezone(timedelta(hours=-utc_offset))
        dt_local = datetime(
            int(date_str[:4]),
            int(date_str[5:7]),
            int(date_str[8:10]),
            hour, minute, 0, tzinfo=local_tz
        )
        
        # Converter para São Paulo
        dt_sp = dt_local.astimezone(TIMEZONE_SP)
        
        date_sp = dt_sp.strftime("%Y-%m-%d")
        time_sp = dt_sp.strftime("%H:%M")
        
        return date_sp, time_sp
    except (ValueError, IndexError) as e:
        print(f"  Aviso: Erro ao converter '{date_str} {time_str}': {e}")
        return date_str, time_part if 'time_part' in locals() else time_str


def format_score(score: dict) -> str:
    """Formata o placar para exibição, incluindo prorrogação e pênaltis se disponíveis."""
    ft = score.get("ft", [])
    if len(ft) == 2:
        result = f"{ft[0]} x {ft[1]}"
        
        # Adicionar prorrogação se existir
        et = score.get("et", [])
        if len(et) == 2 and et != ft:
            result += f" (prorrogação: {et[0]} x {et[1]})"
        
        # Adicionar pênaltis se existir
        p = score.get("p", [])
        if len(p) == 2:
            result += f" (pênaltis: {p[0]} x {p[1]})"
        
        return result
    return "-"


def format_score_short(score: dict) -> str:
    """Formata placar curto para classificação."""
    ft = score.get("ft", [])
    if len(ft) == 2:
        return f"{ft[0]} x {ft[1]}"
    return "-"


def determine_stage(round_name: str, group: str) -> str:
    """Determina a fase/grupo da partida."""
    if group:
        return group
    
    round_lower = round_name.lower()
    if "round of 16" in round_lower or "oitavas" in round_lower:
        return "Round of 16"
    if "quarter" in round_lower or "quartas" in round_lower:
        return "Quarterfinals"
    if "semi" in round_lower:
        return "Semifinals"
    if "final" in round_lower:
        return "Final"
    if "third" in round_lower or "terceiro" in round_lower:
        return "Third Place"
    return round_name


def format_date_br(date_str: str) -> str:
    """Formata data para o padrão brasileiro."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except ValueError:
        return date_str


def load_existing_data(filepath: str) -> dict:
    """Carrega dados existentes do arquivo JSON."""
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def matches_are_equal(existing: list, new: list) -> bool:
    """Compara se os dados das partidas são iguais, ignorando campos calculados."""
    if len(existing) != len(new):
        return False
    
    for exp, new_match in zip(existing, new):
        # Comparar campos da fonte (não os calculados)
        source_fields = ["round", "date", "time", "team1", "team2", "score", "goals1", "goals2", "group", "ground", "num"]
        for field in source_fields:
            if exp.get(field) != new_match.get(field):
                return False
    
    return True


def save_json(data: dict, filepath: str, force: bool = False):
    """Salva o JSON processado. Retorna True se houve alteração."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # Dados das partidas para comparação (sem campos calculados)
    new_matches_for_compare = []
    for m in data.get("matches", []):
        match_copy = {k: v for k, v in m.items() if k in [
            "round", "date", "time", "team1", "team2", "score", 
            "goals1", "goals2", "group", "ground", "num"
        ]}
        new_matches_for_compare.append(match_copy)
    
    existing_data = load_existing_data(filepath)
    existing_matches = existing_data.get("matches", [])
    
    if not force and matches_are_equal(existing_matches, new_matches_for_compare):
        print("Dados das partidas inalterados. Pulando gravação.")
        return False
    
    output = {
        "last_updated": datetime.now(ZoneInfo("UTC")).isoformat(),
        "source": SOURCE_URL,
        "name": data.get("name", "World Cup 2026"),
        "matches": data.get("matches", [])
    }
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"JSON salvo em: {filepath}")
    return True


def generate_html(data: dict):
    """Gera a página HTML com as partidas. Retorna True se houve alteração."""
    matches = data.get("matches", [])
    
    html = '''<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Copa do Mundo FIFA 2026</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background: #fafafa;
            color: #333;
        }
        h1 {
            text-align: center;
            color: #1a1a2e;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
        }
        table {
            margin: auto;
            border-collapse: collapse;
            width: 95%;
            max-width: 1000px;
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        th, td {
            padding: 12px 15px;
            border: 1px solid #ddd;
            text-align: center;
        }
        th {
            background-color: #1a1a2e;
            color: white;
        }
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        .team {
            font-weight: bold;
            text-align: left;
        }
        .score {
            font-size: 18px;
            font-weight: bold;
            color: #1a1a2e;
        }
        .score-detail {
            font-size: 12px;
            color: #666;
            display: block;
            margin-top: 2px;
        }
        .stage-header {
            background-color: #e8e8e8;
            font-weight: bold;
            text-align: left;
        }
        .group {
            color: #666;
            font-size: 14px;
        }
        .time {
            color: #444;
            font-size: 14px;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
        }
        .footer a {
            color: #007BFF;
            text-decoration: none;
        }
        .footer a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <h1>Copa do Mundo FIFA 2026</h1>
    <p class="subtitle">Estados Unidos · México · Canadá | 11 de Junho - 19 de Julho de 2026</p>
    
    <table>
        <thead>
            <tr>
                <th>Data</th>
                <th>Horário (SP)</th>
                <th>Equipe 1</th>
                <th>Placar</th>
                <th>Equipe 2</th>
                <th>Fase/Grupo</th>
                <th>Estádio</th>
            </tr>
        </thead>
        <tbody>
'''
    
    current_stage = ""
    for match in matches:
        stage = match.get("stage", match.get("round", ""))
        
        if stage != current_stage:
            if current_stage != "":
                html += '        </tbody>\n        <tbody>\n'
            html += f'''            <tr class="stage-header">
                <td colspan="7">{stage}</td>
            </tr>
'''
            current_stage = stage
        
        date_sp = match.get("date_sp", match.get("date", "-"))
        time_sp = match.get("time_sp", "-")
        team1 = match.get("team1", "-")
        team2 = match.get("team2", "-")
        score_obj = match.get("score", {})
        score_display = format_score(score_obj)
        ground = match.get("ground", "-")
        
        # Separar placar principal e detalhes
        ft = score_obj.get("ft", [])
        et = score_obj.get("et", [])
        p = score_obj.get("p", [])
        
        if et or p:
            main_score = f"{ft[0]} x {ft[1]}" if len(ft) == 2 else "-"
            extra_parts = []
            if et and et != ft:
                extra_parts.append(f"PR: {et[0]}x{et[1]}")
            if p:
                extra_parts.append(f"PEN: {p[0]}x{p[1]}")
            score_html = f'{main_score}<span class="score-detail">{" | ".join(extra_parts)}</span>'
        else:
            score_html = score_display
        
        date_formatted = format_date_br(date_sp)
        
        html += f'''            <tr>
                <td>{date_formatted}</td>
                <td class="time">{time_sp}</td>
                <td class="team">{team1}</td>
                <td class="score">{score_html}</td>
                <td class="team">{team2}</td>
                <td class="group">{stage}</td>
                <td>{ground}</td>
            </tr>
'''
    
    last_updated = datetime.now(TIMEZONE_SP).strftime("%d/%m/%Y às %H:%M")
    
    html += f'''        </tbody>
    </table>
    <p class="footer">Dados atualizados em: {last_updated} (horário de Brasília) | <a href="../index.html">← Voltar ao site</a></p>
</body>
</html>'''
    
    # Verificar se o HTML mudou
    existing_html = ""
    if os.path.exists(OUTPUT_HTML):
        with open(OUTPUT_HTML, "r", encoding="utf-8") as f:
            existing_html = f.read()
    
    if existing_html == html:
        print("HTML inalterado.")
        return False
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"HTML gerado em: {OUTPUT_HTML}")
    return True


def main():
    print("=" * 50)
    print("Copa do Mundo FIFA 2026 - Atualizador de Dados")
    print("=" * 50)
    
    print(f"\nBaixando dados da Copa do Mundo 2026...")
    data = download_json(SOURCE_URL)
    
    matches = data.get("matches", [])
    print(f"Encontradas {len(matches)} partidas\n")
    
    print("Convertendo horários para America/Sao_Paulo...")
    for match in matches:
        date = match.get("date", "")
        time_str = match.get("time", "")
        utc_offset = parse_utc_offset(time_str)
        date_sp, time_sp = convert_to_sao_paulo(date, time_str, utc_offset)
        
        match["date_sp"] = date_sp
        match["time_sp"] = time_sp
        match["score_display"] = format_score(match.get("score", {}))
        match["stage"] = determine_stage(
            match.get("round", ""),
            match.get("group", "")
        )
    
    matches.sort(key=lambda m: f"{m.get('date_sp', '')} {m.get('time_sp', '')}")
    
    # Salvar JSON apenas se dados das partidas mudaram
    json_changed = save_json(data, DATA_FILE)
    
    # Gerar HTML apenas se dados mudaram
    html_changed = generate_html(data)
    
    if not json_changed and not html_changed:
        print("\n" + "=" * 50)
        print("Nenhuma alteração detectada. Encerrando.")
        print("=" * 50)
        return
    
    print("\n" + "=" * 50)
    print("Atualização concluída com sucesso!")
    print("=" * 50)


if __name__ == "__main__":
    main()
