#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def request(base_url: str, path: str) -> tuple[int, str]:
    url = f"{base_url.rstrip('/')}{path}"

    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Self-hosted Smart Document RAG saglik kontrolu.",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8080",
    )
    arguments = parser.parse_args()

    checks = (
        ("Frontend", "/", {200}),
        ("Backend", "/health", {200}),
        ("Veritabani", "/health/db", {200}),
        ("Kimlik korumasi", "/api/auth/me", {401}),
    )

    failed = False

    for label, path, accepted_statuses in checks:
        try:
            status, body = request(arguments.base_url, path)
        except OSError as error:
            print(f"KALDI - {label}: {error}")
            failed = True
            continue

        passed = status in accepted_statuses
        print(f"{'GECTI' if passed else 'KALDI'} - {label}: HTTP {status}")

        if not passed:
            failed = True
            try:
                print(json.dumps(json.loads(body), ensure_ascii=False))
            except (json.JSONDecodeError, TypeError):
                print(body[:300])

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
