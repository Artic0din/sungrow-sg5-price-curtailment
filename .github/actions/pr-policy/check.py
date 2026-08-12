#!/usr/bin/env python3
"""Validate host-neutral pull-request metadata from a GitHub event payload."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

CONVENTIONAL_TYPES = (
    "feat",
    "fix",
    "test",
    "refactor",
    "perf",
    "docs",
    "style",
    "chore",
    "ci",
    "build",
    "revert",
)
CONVENTIONAL_TYPE_PATTERN = "|".join(map(re.escape, CONVENTIONAL_TYPES))
CONVENTIONAL_TITLE = re.compile(
    rf"^(?:{CONVENTIONAL_TYPE_PATTERN})"
    r"(?:\([a-z0-9][a-z0-9._/-]*\))?!?: .+"
)
ISSUE_BRANCH = re.compile(
    rf"^(?:{CONVENTIONAL_TYPE_PATTERN}|cursor|issue)/(\d+)(?:-|$)",
    re.IGNORECASE,
)
ISSUE_LINK = re.compile(r"(?i)\b(?:fixes|closes|resolves)\s+#(\d+)\b")
VALIDATION_SECTION = re.compile(
    r"(?ims)^#{1,3}\s+(?:test plan|tests?|validation|verification)\s*$"
    r"(?P<content>.*?)(?=^#{1,3}\s+|\Z)"
)
NEGATIVE_VALIDATION = re.compile(
    r"(?i)(?:^|:\s*)(?:n/?a|none|not applicable|not required|not run|"
    r"not tested|pending|skipped|todo)(?:\b|[.!])|"
    r"\btests?\s+(?:were\s+|was\s+)?not\s+(?:run|tested)\b"
)
VALIDATION_SCAFFOLD = re.compile(
    r"(?i)^(?:results?|commands?|evidence|checks?|tests?|validation|verification):$"
)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
FENCED_CODE = re.compile(
    r"(?ms)^[ \t]*(?P<fence>`{3,}|~{3,})[^\n]*\n.*?^[ \t]*(?P=fence)[ \t]*$"
)
GRAPHITE_QUEUE_BRANCH = re.compile(r"^gtmq_[A-Za-z0-9_-]+$")
GRAPHITE_QUEUE_TITLE_PREFIX = "[Graphite MQ] Draft PR GROUP:"
GRAPHITE_QUEUE_AUTHOR = "graphite-app[bot]"
IssueLookup = Callable[[int], tuple[bool, str]]


def validate_pull_request(
    pull_request: dict[str, Any], issue_lookup: IssueLookup | None = None
) -> list[str]:
    if is_graphite_queue_pull_request(pull_request):
        return []
    failures: list[str] = []
    title = str(pull_request.get("title") or "")
    body = HTML_COMMENT.sub("", str(pull_request.get("body") or ""))
    linkable_body = FENCED_CODE.sub("", body)
    branch = str(pull_request.get("head", {}).get("ref") or "")
    if pull_request.get("draft"):
        failures.append("pull request must be ready for review, not draft")
    if not CONVENTIONAL_TITLE.fullmatch(title):
        failures.append("pull-request title is not conventional")
    if not body.strip():
        failures.append("pull-request body is empty")
    elif not (validation_matches := list(VALIDATION_SECTION.finditer(body))):
        failures.append("pull-request body lacks a test or validation section")
    elif not any(
        meaningful_validation(match.group("content")) for match in validation_matches
    ):
        failures.append("pull-request validation section has no verification evidence")
    issue_match = ISSUE_BRANCH.search(branch)
    if issue_match:
        issue_number = issue_match.group(1)
        linked = {match.group(1) for match in ISSUE_LINK.finditer(linkable_body)}
        if linked != {issue_number}:
            failures.append(
                f"issue-backed pull request must close only issue #{issue_number}"
            )
        elif issue_lookup is not None:
            issue_is_open, issue_failure = issue_lookup(int(issue_number))
            if not issue_is_open:
                failures.append(issue_failure)
    return failures


def github_issue_lookup(issue_number: int) -> tuple[bool, str]:
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("AGENT_POLICY_GITHUB_TOKEN", "")
    api_url = os.environ.get("GITHUB_API_URL", "https://api.github.com")
    if not repository or not token:
        return False, f"unable to verify linked issue #{issue_number}"
    request = urllib.request.Request(
        f"{api_url}/repos/{repository}/issues/{issue_number}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "agent-delivery-policy",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            issue = json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return False, f"linked issue #{issue_number} does not exist"
        return (
            False,
            f"unable to verify linked issue #{issue_number}: HTTP {error.code}",
        )
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        return False, f"unable to verify linked issue #{issue_number}: {error}"
    if issue.get("pull_request") is not None:
        return False, f"linked item #{issue_number} is a pull request, not an issue"
    return True, ""


def is_graphite_queue_pull_request(pull_request: dict[str, Any]) -> bool:
    """Recognize Graphite's authenticated synthetic queue pull request."""
    title = str(pull_request.get("title") or "")
    branch = str(pull_request.get("head", {}).get("ref") or "")
    author = str(pull_request.get("user", {}).get("login") or "")
    return bool(
        pull_request.get("draft")
        and GRAPHITE_QUEUE_BRANCH.fullmatch(branch)
        and title.startswith(GRAPHITE_QUEUE_TITLE_PREFIX)
        and author == GRAPHITE_QUEUE_AUTHOR
    )


def meaningful_validation(content: str) -> bool:
    for line in content.splitlines():
        stripped = line.strip().lstrip("-* ").strip()
        if re.fullmatch(
            r"`{3,}(?:[A-Za-z0-9_+-]+)?|~{3,}(?:[A-Za-z0-9_+-]+)?", stripped
        ):
            continue
        if re.match(r"^\[\s\]", stripped):
            continue
        stripped = re.sub(r"^\[[ xX]\]\s*", "", stripped)
        for clause in stripped.split(";"):
            clause = clause.strip()
            if not clause:
                continue
            if ISSUE_LINK.fullmatch(clause):
                continue
            if VALIDATION_SCAFFOLD.fullmatch(clause):
                continue
            if NEGATIVE_VALIDATION.search(clause):
                continue
            return True
    return False


def render(failures: list[str]) -> str:
    if not failures:
        return "PASS: pull-request policy is satisfied.\n"
    return "FAIL:\n" + "\n".join(f"- {failure}" for failure in failures) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.event.read_text(encoding="utf-8"))
    pull_request = payload.get("pull_request")
    if not isinstance(pull_request, dict):
        parser.error("event payload does not contain a pull_request object")
    failures = validate_pull_request(pull_request, issue_lookup=github_issue_lookup)
    print(render(failures), end="")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
