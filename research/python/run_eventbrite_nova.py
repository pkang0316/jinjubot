from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from jinjubot_research.bounded_crawl import run_bounded_source_scan
from jinjubot_research.config import DiscoveryConfig, load_env_file
from jinjubot_research.local_digest import merge_event_items, read_existing_digest, write_digest


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    load_env_file(repo_root / "infra" / ".env.local")

    config = DiscoveryConfig.from_env()
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    result = run_bounded_source_scan(config, generated_at)

    digest_path = repo_root / "content" / "research-digest.json"
    existing = read_existing_digest(digest_path, generated_at)
    payload = merge_event_items(existing, result["items"], generated_at, result["summary"])
    write_digest(digest_path, payload)

    print(f"Wrote {len(result['items'])} bounded-crawl event record(s) to {digest_path}")
    print("Fetched follow-up URLs:")
    for source_run in result["source_runs"]:
        for event_url in source_run["selected_urls"]:
            print(f"- {event_url}")


if __name__ == "__main__":
    main()
