"""Check the checked-in update manifest expiry (PROJECT_AUDIT.md Phase 1.3).

Exit 0 when `updates/latest.json` is valid for more than --warn-days.
Exit 2 when it expires within --warn-days (CI warning).
Exit 1 when it is already expired, unreadable, or invalid.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

# NOTE: CI dependency-free intentionally — this script must run on a bare
# setup-python runner with stdlib only. Do NOT import src.core.update_manifest
# (it pulls in `cryptography`); keep the default in sync with
# MANIFEST_EXPIRY_WARN_DAYS there.
DEFAULT_WARN_DAYS = 30


def check_manifest(manifest_path: Path, warn_days: int) -> tuple[int, str]:
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return 1, f"cannot read manifest {manifest_path}: {exc}"
    payload = document.get("payload") if isinstance(document, dict) else None
    if not isinstance(payload, dict):
        return 1, f"manifest payload is missing in {manifest_path}"
    try:
        expires_at = datetime.fromisoformat(str(payload.get("expires_at", "")).replace("Z", "+00:00"))
    except ValueError:
        return 1, f"manifest expires_at is invalid in {manifest_path}"
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    if expires_at <= now:
        return 1, f"update manifest expired at {expires_at.isoformat()} — re-publish a release"
    days_left = int((expires_at - now).total_seconds() // 86400)
    if days_left <= warn_days:
        return 2, f"update manifest expires in {days_left} days ({expires_at.isoformat()}) — re-publish soon"
    return 0, f"update manifest valid for {days_left} more days"


def main() -> int:
    parser = argparse.ArgumentParser(description="Warn before the update manifest expires")
    parser.add_argument("--manifest", default="updates/latest.json")
    parser.add_argument("--warn-days", type=int, default=DEFAULT_WARN_DAYS)
    args = parser.parse_args()
    code, message = check_manifest(Path(args.manifest), args.warn_days)
    print(message)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
