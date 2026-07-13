"""Read-only smoke test for a running NotebookLM Gateway instance."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

import httpx


def request_json(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    token: str | None = None,
) -> Any:
    headers = {"Authorization": f"Bearer {token}"} if token else None
    response = client.request(method, path, headers=headers)
    response.raise_for_status()
    return response.json()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.getenv("GATEWAY_BASE_URL", "http://127.0.0.1:18388"),
        help="Gateway origin; defaults to GATEWAY_BASE_URL or localhost",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("GATEWAY_USER_API_KEY"),
        help="User API key; defaults to GATEWAY_USER_API_KEY",
    )
    parser.add_argument(
        "--notebook-id",
        default=None,
        help="Optionally inspect sources and artifacts for one notebook",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.api_key:
        print("Set GATEWAY_USER_API_KEY or pass --api-key.", file=sys.stderr)
        return 2

    try:
        with httpx.Client(base_url=args.base_url.rstrip("/"), timeout=20) as client:
            health = request_json(client, "GET", "/healthz")
            info = request_json(client, "GET", "/v1/server/info", token=args.api_key)
            notebooks = request_json(client, "GET", "/v1/notebooks", token=args.api_key)
            print(f"health: {health.get('status')}")
            print(
                f"gateway: {info.get('version')} | sdk: {info.get('sdk_version')} | "
                f"account: {info.get('account', {}).get('email')}"
            )
            print(f"notebooks: {len(notebooks.get('notebooks', []))}")

            if args.notebook_id:
                prefix = f"/v1/notebooks/{args.notebook_id}"
                sources = request_json(client, "GET", f"{prefix}/sources", token=args.api_key)
                artifacts = request_json(client, "GET", f"{prefix}/artifacts", token=args.api_key)
                print(f"sources: {len(sources.get('sources', []))}")
                print(f"artifacts: {len(artifacts.get('artifacts', []))}")
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500]
        print(f"HTTP {exc.response.status_code}: {detail}", file=sys.stderr)
        return 1
    except httpx.HTTPError as exc:
        print(f"Connection failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
