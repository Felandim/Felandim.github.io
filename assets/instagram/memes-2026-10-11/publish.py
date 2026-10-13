"""Publicação única do carrossel aprovado, sem alterar a automação diária."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from PIL import Image

ROOT = Path(__file__).resolve().parent
API_ROOT = "https://graph.instagram.com/v23.0"


class PublishError(RuntimeError):
    """Erro seguro para logs públicos, sem respostas brutas ou credenciais."""


def load_manifest() -> dict:
    manifest = json.loads((ROOT / "publish.json").read_text(encoding="utf-8"))
    if manifest["account_id"] != "17841429981371844" or manifest["username"] != "brasileiraoemrodadas":
        raise PublishError("A conta não corresponde à publicação autorizada.")
    if len(manifest["images"]) != 3 or not 0 < len(manifest["caption"]) <= 2200:
        raise PublishError("Quantidade de imagens ou legenda inválida.")
    for item in manifest["images"]:
        name = item["file"]
        if Path(name).name != name or not name.endswith(".jpg"):
            raise PublishError("Caminho de imagem inválido.")
        path = ROOT / name
        content = path.read_bytes()
        if len(content) >= 8_000_000 or hashlib.sha256(content).hexdigest() != item["sha256"]:
            raise PublishError("A imagem difere da versão aprovada.")
        with Image.open(path) as image:
            if image.format != "JPEG" or image.size != (1080, 1350) or image.mode != "RGB":
                raise PublishError("A imagem precisa ser JPEG RGB de 1080 por 1350.")
    return manifest


class Instagram:
    def __init__(self, token: str):
        if not token:
            raise PublishError("INSTAGRAM_ACCESS_TOKEN não está configurado.")
        self.headers = {"Authorization": f"Bearer {token}"}

    def request(self, method: str, path: str, **params) -> dict:
        url = f"{API_ROOT}/{path}"
        body = None
        if method == "GET":
            url += "?" + urlencode(params)
        else:
            body = urlencode(params).encode("utf-8")
        try:
            try:
                response = urlopen(Request(url, data=body, headers=self.headers, method=method), timeout=45)
            except HTTPError as error:
                response = error
            with response:
                status = response.code
                payload = json.loads(response.read())
        except (URLError, OSError, ValueError):
            raise PublishError(f"Falha de transporte na etapa {method}; publicação não será repetida automaticamente.") from None
        if status >= 400 or "error" in payload:
            error = payload.get("error", {})
            raise PublishError(
                f"Instagram retornou HTTP {status}; "
                f"código {error.get('code', 'não informado')}, "
                f"subcódigo {error.get('error_subcode', 'não informado')}."
            )
        return payload

    def ready(self, container_id: str) -> None:
        for _ in range(60):
            status = self.request("GET", container_id, fields="status_code").get("status_code")
            if status == "FINISHED":
                return
            if status in {"ERROR", "EXPIRED", "PUBLISHED"}:
                raise PublishError(f"Container em estado inesperado: {status}.")
            time.sleep(2)
        raise PublishError("O processamento do container excedeu dois minutos.")


def verified_media(api: Instagram, media_id: str) -> dict:
    media = api.request("GET", media_id, fields="id,media_type,permalink,children.limit(10){id,media_type}")
    if media.get("media_type") != "CAROUSEL_ALBUM" or len(media.get("children", {}).get("data", [])) != 3:
        raise PublishError(f"Publicação {media_id} criada, mas a confirmação do carrossel de três imagens falhou. Não republicar.")
    return {"media_id": media_id, "permalink": media.get("permalink"), "slides": 3}


def publish(manifest: dict, api: Instagram, source_base: str) -> dict:
    account_id = manifest["account_id"]
    profile = api.request("GET", account_id, fields="id,username")
    if str(profile.get("id")) != account_id or profile.get("username") != manifest["username"]:
        raise PublishError("A identidade retornada pelo Instagram não corresponde à conta autorizada.")
    # A leitura precisa funcionar antes de qualquer criação, para impedir duplicação.
    recent = api.request("GET", f"{account_id}/media", fields="id,caption", limit=100)
    for media in recent.get("data", []):
        if media.get("caption") == manifest["caption"]:
            return {"outcome": "already_published", **verified_media(api, media["id"])}

    # Confere bytes públicos, sem transmitir o token do Instagram ao host de imagens.
    urls = []
    for item in manifest["images"]:
        url = f"{source_base}/{item['file']}"
        try:
            with urlopen(url, timeout=30) as response:
                content = response.read()
        except (URLError, OSError):
            raise PublishError("Não foi possível baixar uma imagem pública.") from None
        if hashlib.sha256(content).hexdigest() != item["sha256"]:
            raise PublishError("Uma imagem pública não corresponde ao arquivo aprovado.")
        urls.append(url)

    children = []
    for index, url in enumerate(urls, 1):
        child = api.request("POST", f"{account_id}/media", image_url=url, is_carousel_item="true")
        api.ready(child["id"])
        children.append(child["id"])
        print(f"Imagem {index}/3 processada.", flush=True)
    parent = api.request(
        "POST", f"{account_id}/media", media_type="CAROUSEL",
        children=",".join(children), caption=manifest["caption"],
    )
    api.ready(parent["id"])
    # Não repetir esta chamada: um timeout não comprova que a publicação falhou.
    published = api.request("POST", f"{account_id}/media_publish", creation_id=parent["id"])
    media_id = published["id"]
    print(json.dumps({"outcome": "published_pending_verification", "media_id": media_id}), flush=True)
    return {"outcome": "published", **verified_media(api, media_id)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    manifest = load_manifest()
    if not args.publish:
        print(json.dumps({"validated": True, "username": manifest["username"], "slides": 3, "caption_length": len(manifest["caption"])}))
        return
    if datetime.now(timezone.utc) >= datetime(2026, 10, 14, 12, tzinfo=timezone.utc):
        raise PublishError("A janela desta publicação única expirou; é necessária nova autorização.")
    sha = os.environ.get("GITHUB_SHA", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not re.fullmatch(r"[0-9a-f]{40}", sha) or repo != "Felandim/Felandim.github.io":
        raise PublishError("A publicação deve executar no repositório autorizado e usar imagens de um commit imutável.")
    source_base = f"https://raw.githubusercontent.com/{repo}/{sha}/assets/instagram/memes-2026-10-11"
    receipt = publish(manifest, Instagram(os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")), source_base)
    print(json.dumps(receipt, ensure_ascii=False), flush=True)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as output:
            output.write(f"### Carrossel de memes\n\n{receipt['outcome']} — {receipt['slides']} imagens\n\n{receipt.get('permalink') or receipt['media_id']}\n")


if __name__ == "__main__":
    try:
        main()
    except PublishError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from None
