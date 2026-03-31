#!/usr/bin/env python3
"""Send dialog turns from YAML files to the chatbot API sequentially."""

import argparse
import glob
import sys
import yaml
import requests


def load_dialog(path: str) -> tuple[list[str], str | None]:
    """Load dialog turns and optional session ID from a YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    turns = [t["user"] for t in data.get("turns", [])]
    session_id = data.get("session_id")
    return turns, session_id


def send_message(base_url: str, query: str, session_id: str | None) -> dict:
    """POST a chat message to the API and return the response as a dict."""
    payload = {"query": query}
    if session_id:
        payload["session_id"] = session_id
    response = requests.post(f"{base_url}/chat", json=payload, timeout=120)
    response.raise_for_status()
    return response.json()


def run_dialog(base_url: str, path: str) -> None:
    """Load and execute all turns in a dialog YAML file against the chat API."""
    turns, session_id = load_dialog(path)
    if not turns:
        print("  No turns found — skipping.")
        return

    print(f"  Session : {session_id or '(none)'}")
    print(f"  Turns   : {len(turns)}")

    for i, message in enumerate(turns, start=1):
        print(f"\n  [{i}/{len(turns)}] You: {message}")
        try:
            result = send_message(base_url, message, session_id)
            print(f"           Bot: {result['reply']}")
            if result.get("intent"):
                print(f"                (intent: {result['intent']})")
        except requests.exceptions.ConnectionError:
            print(f"\nERROR: Could not connect to {base_url}. Is the server running?")
            sys.exit(1)
        except requests.exceptions.HTTPError as e:
            print(f"\nERROR: HTTP {e.response.status_code} — {e.response.text}")


def main():
    """Parse CLI arguments and run dialog files against the chatbot API."""
    parser = argparse.ArgumentParser(description="Run chatbot dialogs from YAML files")
    parser.add_argument(
        "--dialogs-dir",
        default="data/dialogs",
        help="Directory containing dialog YAML files (default: data/dialogs)",
    )
    parser.add_argument(
        "--dialog",
        help="Path to a single dialog YAML file (overrides --dialogs-dir)",
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL of the chatbot API (default: http://localhost:8000)",
    )
    args = parser.parse_args()

    if args.dialog:
        files = [args.dialog]
    else:
        files = sorted(glob.glob(f"{args.dialogs_dir}/*.yaml"))
        if not files:
            print(f"No YAML files found in '{args.dialogs_dir}'.")
            sys.exit(1)

    print(f"Found {len(files)} dialog(s)  |  Target: {args.url}\n")

    for idx, path in enumerate(files, start=1):
        print("=" * 60)
        print(f"Dialog {idx}/{len(files)}: {path}")
        run_dialog(args.url, path)
        print()

    print("=" * 60)
    print("Done.")


if __name__ == "__main__":
    main()
