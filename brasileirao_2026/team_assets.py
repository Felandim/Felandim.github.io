"""Identidade visual compartilhada dos times do Brasileirão 2026."""

from __future__ import annotations

import html
from typing import Any


TEAM_LOGO_IDS = {
    "Athletico-PR": 10273,
    "Atlético-MG": 10272,
    "Bahia": 7877,
    "Botafogo": 8517,
    "Bragantino": 109705,
    "Chapecoense": 197693,
    "Corinthians": 9808,
    "Coritiba": 9767,
    "Cruzeiro": 9781,
    "Flamengo": 9770,
    "Fluminense": 9863,
    "Grêmio": 9769,
    "Internacional": 8702,
    "Mirassol": 163782,
    "Palmeiras": 10283,
    "Remo": 1626,
    "Santos": 8514,
    "São Paulo": 10277,
    "Vasco": 10276,
    "Vitória": 7733,
}

TEAM_THEMES = {
    "Athletico-PR": ("#b5122b", "#ffffff"),
    "Atlético-MG": ("#161616", "#ffffff"),
    "Bahia": ("#0057a8", "#ffffff"),
    "Botafogo": ("#161616", "#ffffff"),
    "Bragantino": ("#b51e2e", "#ffffff"),
    "Chapecoense": ("#006847", "#ffffff"),
    "Corinthians": ("#161616", "#ffffff"),
    "Coritiba": ("#006847", "#ffffff"),
    "Cruzeiro": ("#0057a8", "#ffffff"),
    "Flamengo": ("#b5122b", "#ffffff"),
    "Fluminense": ("#6f1735", "#ffffff"),
    "Grêmio": ("#087db8", "#ffffff"),
    "Internacional": ("#b5122b", "#ffffff"),
    "Mirassol": ("#f0cf16", "#101714"),
    "Palmeiras": ("#006437", "#ffffff"),
    "Remo": ("#003f7f", "#ffffff"),
    "Santos": ("#161616", "#ffffff"),
    "São Paulo": ("#b5122b", "#ffffff"),
    "Vasco": ("#161616", "#ffffff"),
    "Vitória": ("#b5122b", "#ffffff"),
}


def team_logo_url(team: str) -> str:
    return f"https://images.fotmob.com/image_resources/logo/teamlogo/{TEAM_LOGO_IDS[team]}.png"


def team_badge_image(
    team: str,
    *,
    css_class: str = "br-team-badge",
    attributes: dict[str, Any] | None = None,
) -> str:
    attrs = {
        "class": css_class,
        "src": team_logo_url(team),
        "alt": "",
        "aria-hidden": "true",
        "width": "48",
        "height": "48",
        "loading": "lazy",
        "decoding": "async",
        **(attributes or {}),
    }
    rendered = " ".join(
        f'{html.escape(str(name), quote=True)}="{html.escape(str(value), quote=True)}"'
        for name, value in attrs.items()
    )
    return f"<img {rendered}>"


def team_badge(team: str, variant: str = "inline") -> str:
    """Renderiza escudo e nome como uma unidade proporcional à tipografia."""
    safe_team = html.escape(team)
    return (
        f'<span class="br-team-with-badge br-team-with-badge-{variant}">'
        f"{team_badge_image(team)}<span>{safe_team}</span></span>"
    )


def team_badge_list(teams: list[str], variant: str = "inline", empty: str = "ninguém") -> str:
    return ", ".join(team_badge(team, variant) for team in teams) if teams else html.escape(empty)


def team_theme(team: str) -> tuple[str, str]:
    return TEAM_THEMES[team]
