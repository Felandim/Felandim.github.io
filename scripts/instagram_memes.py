"""Publish three original memes only for a confirmed newly published round block."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "data/instagram_memes_published.json"
ASSETS = ROOT / "assets/instagram/memes-blocks"
API_ROOT = "https://graph.instagram.com/v23.0"
ACCOUNT = "17841429981371844"
PROFILE = "27834175349616492"
USERNAME = "brasileiraoemrodadas"
CUTOFF = datetime.fromisoformat("2026-10-13T15:09:40-03:00")
class PublishError(RuntimeError):
    """Safe error with no token or raw API response."""

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


def read_json(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def checkpoint(block_id, **updates):
    # Persist before publishing: a timeout must never cause another media_publish.
    state = read_json(STATE, {})
    state.setdefault(block_id, {}).update(updates, updated_at=datetime.now(timezone.utc).isoformat())
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if os.getenv("GITHUB_ACTIONS") != "true":
        raise PublishError("Durable publication checkpoints require GitHub Actions.")
    commands = [
        ["git", "add", "data/instagram_memes_published.json"],
        ["git", "commit", "-m", f"Record meme block {block_id}: {updates.get('state', 'checkpoint')}"],
        ["git", "pull", "--rebase", "origin", "main"],
        ["git", "push", "origin", "HEAD:main"],
    ]
    for command in commands:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        if result.returncode:
            raise PublishError("Could not persist the publication checkpoint; no further publication call will run.")


def eligible(block):
    try:
        return (block.get("outcome") == "published" and bool(block.get("media_id"))
                and datetime.fromisoformat(block["published_at"]) > CUTOFF)
    except (KeyError, ValueError, TypeError):
        return False


def account_media(api):
    profile = api.request("GET", ACCOUNT, fields="id,username")
    if str(profile.get("id")) != PROFILE or profile.get("username") != USERNAME:
        raise PublishError("Instagram account identity differs from the authorized account.")
    rows, after = [], None
    while True:
        params = {"fields": "id,caption,timestamp,media_type,permalink", "limit": 100}
        if after:
            params["after"] = after
        page = api.request("GET", f"{ACCOUNT}/media", **params)
        rows.extend(page.get("data", []))
        paging = page.get("paging", {})
        next_after = paging.get("cursors", {}).get("after")
        if not paging.get("next"):
            return rows
        if not next_after or next_after == after:
            raise PublishError("Could not exhaust account media for duplicate detection.")
        after = next_after


def verified_media(api, media_id):
    media = api.request("GET", media_id, fields="id,media_type,permalink,children.limit(10){id,media_type}")
    children = media.get("children", {}).get("data", [])
    if (media.get("media_type") != "CAROUSEL_ALBUM" or len(children) != 3
            or any(child.get("media_type") != "IMAGE" for child in children)
            or not str(media.get("permalink", "")).startswith("https://www.instagram.com/")):
        raise PublishError("Carousel verification failed; do not republish.")
    return {"carousel_id": str(media_id), "permalink": media["permalink"],
            "child_media_ids": [x["id"] for x in children], "slides": 3}


def validate_manifest(path, block_id, block, matches):
    manifest = read_json(path)
    if not re.fullmatch(r"[a-f0-9]{20}", block_id) or manifest.get("block_id") != block_id:
        raise PublishError("Invalid source block.")
    if not eligible(block) or str(manifest.get("summary_media_id")) != str(block["media_id"]):
        raise PublishError("Summary is not an eligible published block.")
    keys = block.get("match_keys", [])
    if not keys or len(keys) != len(set(keys)) or manifest.get("match_keys") != keys:
        raise PublishError("Manifest must reference exactly the source block match keys.")
    expected_id = hashlib.sha256("\n".join(sorted(keys)).encode()).hexdigest()[:20]
    if expected_id != block_id:
        raise PublishError("Source block identity mismatch.")
    lookup = {json.dumps([m["round"], m["home"], m["away"]], ensure_ascii=False): m for m in matches}
    if any(key not in lookup for key in keys) or len({lookup[key]["round"] for key in keys}) != 1:
        raise PublishError("Source matches missing or mixed rounds.")
    if any(not re.fullmatch(r"\d+\s*x\s*\d+", str(lookup[key].get("score", ""))) for key in keys):
        raise PublishError("Block contains unfinished matches.")
    if manifest.get("account_id") != ACCOUNT or manifest.get("api_profile_id") != PROFILE or manifest.get("username") != USERNAME:
        raise PublishError("Unauthorized manifest account.")
    images = manifest.get("images", [])
    if len(images) != 3 or len({item.get("file") for item in images}) != 3:
        raise PublishError("Exactly three distinct images are required.")
    if not 0 < len(manifest.get("caption", "")) <= 2200 or not manifest.get("reviewed"):
        raise PublishError("Caption or editorial review missing.")
    for item in images:
        name = item.get("file", "")
        if Path(name).name != name or not name.endswith(".jpg") or item.get("match_key") not in keys:
            raise PublishError("Invalid image or out-of-block match.")
        current = lookup[item["match_key"]]
        if any(item.get("match", {}).get(field) != current.get(field) for field in ("round", "home", "away", "score", "date")):
            raise PublishError("Image facts differ from current match data.")
        data = (path.parent / name).read_bytes()
        if len(data) >= 8_000_000 or hashlib.sha256(data).hexdigest() != item.get("sha256"):
            raise PublishError("Image checksum differs from reviewed image.")
        with Image.open(path.parent / name) as image:
            if image.format != "JPEG" or image.mode != "RGB" or image.size != (1080, 1350):
                raise PublishError("Image must be JPEG RGB 1080x1350.")
    if len(keys) >= 3 and len({item["match_key"] for item in images}) != 3:
        raise PublishError("A block of three or more matches requires three distinct games.")
    return manifest


def publish_one(api, manifest, path, block, recent, sha):
    block_id = manifest["block_id"]
    summary = next((m for m in recent if str(m["id"]) == str(block["media_id"])), None)
    if not summary or not summary.get("permalink"):
        raise PublishError("Source summary not confirmed among actual account publications.")
    caption = manifest["caption"]
    state = read_json(STATE, {}).get(block_id, {})
    digest = hashlib.sha256(caption.encode()).hexdigest()
    if state.get("caption_sha256") not in (None, digest):
        raise PublishError("Caption changed after processing began; reconcile before continuing.")
    existing = [m for m in recent if m.get("caption") == caption]
    if len(existing) > 1:
        raise PublishError("Multiple matching account posts found; manual reconciliation required.")
    if existing or state.get("carousel_id"):
        candidate = existing[0]["id"] if existing else state["carousel_id"]
        if not any(str(m["id"]) == str(candidate) for m in recent):
            raise PublishError("Recorded carousel is not in the authorized account.")
        receipt = verified_media(api, candidate)
        checkpoint(block_id, state="published", summary_media_id=block["media_id"],
                   summary_permalink=summary["permalink"], caption_sha256=digest, **receipt,
                   published_at=state.get("published_at") or datetime.now(timezone.utc).isoformat())
        print(json.dumps(receipt), flush=True)
        return
    if state.get("state") in {"publish_requested", "published_pending_verification", "published"}:
        raise PublishError("Prior publication outcome is uncertain; no repeat publication call is allowed.")
    parent = state.get("container_id")
    if not parent:
        urls = []
        for item in manifest["images"]:
            url = f"https://raw.githubusercontent.com/Felandim/Felandim.github.io/{sha}/{path.parent.relative_to(ROOT).as_posix()}/{item['file']}"
            try:
                with urlopen(url, timeout=30) as response:
                    data = response.read()
            except (URLError, OSError):
                raise PublishError("Public source image is unavailable.") from None
            if hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise PublishError("Public image bytes differ from reviewed image.")
            urls.append(url)
        checkpoint(block_id, state="creating_containers", summary_media_id=block["media_id"],
                   summary_permalink=summary["permalink"], caption_sha256=digest, source_commit=sha)
        children = []
        for index, url in enumerate(urls, 1):
            child = api.request("POST", f"{ACCOUNT}/media", image_url=url, is_carousel_item="true")
            api.ready(child["id"])
            children.append(child["id"])
            print(f"Image {index}/3 ready", flush=True)
        parent = api.request("POST", f"{ACCOUNT}/media", media_type="CAROUSEL", children=",".join(children), caption=caption)["id"]
        checkpoint(block_id, state="container_ready", container_id=parent, child_container_ids=children)
    api.ready(parent)
    checkpoint(block_id, state="publish_requested", container_id=parent)
    published = api.request("POST", f"{ACCOUNT}/media_publish", creation_id=parent)
    media_id = published["id"]
    print(json.dumps({"outcome": "published_pending_verification", "media_id": media_id}), flush=True)
    checkpoint(block_id, state="published_pending_verification", carousel_id=media_id)
    receipt = verified_media(api, media_id)
    checkpoint(block_id, state="published", **receipt, published_at=datetime.now(timezone.utc).isoformat())
    print(json.dumps(receipt), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    if os.environ.get("GITHUB_REPOSITORY") != "Felandim/Felandim.github.io":
        raise PublishError("This publisher only runs in the authorized repository.")
    sha = os.environ.get("GITHUB_SHA", "")
    if not re.fullmatch(r"[a-f0-9]{40}", sha):
        raise PublishError("Immutable source commit missing.")
    blocks = read_json(ROOT / "data/instagram_blocks_published.json", {})
    api = Instagram(os.environ.get("INSTAGRAM_ACCESS_TOKEN", ""))
    recent = account_media(api)
    for block_id, block in blocks.items():
        if not eligible(block):
            continue
        summary = next((m for m in recent if str(m["id"]) == str(block["media_id"])), None)
        if not summary:
            raise PublishError("Published-block record could not be confirmed on Instagram.")
        print(json.dumps({"block_id": block_id, "summary": summary}), flush=True)
        path = ASSETS / block_id / "publish.json"
        if not path.exists():
            print(f"Block {block_id}: no prepared manifest yet", flush=True)
            continue
        matches = read_json(ROOT / "data/serie_a_2026.json")["matches"]
        manifest = validate_manifest(path, block_id, block, matches)
        if args.publish:
            publish_one(api, manifest, path, block, recent, sha)
    if not args.publish:
        print(json.dumps({"recent_carousels": [m for m in recent if m.get("media_type") == "CAROUSEL_ALBUM"]}), flush=True)


if __name__ == "__main__":
    try:
        main()
    except PublishError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from None

