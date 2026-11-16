#!/usr/bin/env python3
"""Validate Instagram credentials without leaking API responses or secrets."""

from __future__ import annotations

import os
import sys

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class CredentialValidationError(RuntimeError):
    """Safe, user-actionable credential validation failure."""


def _safe_http_error(response: requests.Response) -> str:
    details = [f"HTTP {response.status_code}"]
    try:
        error = response.json().get("error", {})
    except (ValueError, AttributeError):
        error = {}
    if error.get("type"):
        details.append(f"type {error['type']}")
    if error.get("code") is not None:
        details.append(f"code {error['code']}")
    if error.get("error_subcode") is not None:
        details.append(f"subcode {error['error_subcode']}")
    return ", ".join(details)


def _session() -> requests.Session:
    retry = Retry(
        total=4,
        connect=3,
        read=3,
        backoff_factor=2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def validate_token(
    ig_user_id: str,
    token: str,
    api_version: str,
    session: requests.Session | None = None,
) -> str:
    if not token:
        raise CredentialValidationError("INSTAGRAM_ACCESS_TOKEN is not configured")

    client = session or _session()
    base = f"https://graph.instagram.com/{api_version}/{ig_user_id}"
    params = {"access_token": token}
    try:
        profile_response = client.get(
            base,
            params={**params, "fields": "id,username"},
            timeout=30,
        )
        if not profile_response.ok:
            raise CredentialValidationError(_safe_http_error(profile_response))
        profile = profile_response.json()
        if not profile.get("id"):
            raise CredentialValidationError("Instagram API returned no account identifier")

        media_response = client.get(
            f"{base}/media",
            params={**params, "fields": "id", "limit": 1},
            timeout=30,
        )
        if not media_response.ok:
            raise CredentialValidationError(_safe_http_error(media_response))
    except CredentialValidationError:
        raise
    except (requests.RequestException, ValueError, TypeError) as exc:
        raise CredentialValidationError(
            "Instagram API could not be validated due to a network or malformed-response error"
        ) from exc

    return profile.get("username") or "configured account"


def main() -> int:
    try:
        username = validate_token(
            os.environ.get("INSTAGRAM_IG_USER_ID", ""),
            os.environ.get("INSTAGRAM_ACCESS_TOKEN", ""),
            os.environ.get("INSTAGRAM_API_VERSION", "v23.0"),
        )
    except CredentialValidationError as exc:
        print(
            "::error::Instagram credential validation failed "
            f"({exc}). Update INSTAGRAM_ACCESS_TOKEN and verify account permissions.",
            file=sys.stderr,
        )
        return 1
    print(f"Instagram token validated for {username}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
