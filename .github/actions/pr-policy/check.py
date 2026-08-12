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
VALIDATION_HEADINGS = {
    "test",
    "test plan",
    "testing",
    "tests",
    "validation",
    "verification",
}
MARKDOWN_HEADING = re.compile(
    r"^(?P<marks>#{1,6})\s+(?P<title>.*?)(?:\s+#+)?\s*$"
)
FENCE_MARKER = re.compile(r"^\s*(?P<fence>`{3,}|~{3,})")
NEGATIVE_VALIDATION = re.compile(
    r"(?i)(?:^|:\s*)(?:n/?a|none|not applicable|not required|not run|"
    r"not tested|pending|skipped|todo)(?:\b|[.!])|"
    r"\btests?\s+(?:were\s+|was\s+)?not\s+(?:run|tested)\b|"
    r"\bno\s+tests?\s+(?:were\s+)?(?:run|required|needed)\b|"
    r"\bthere\s+(?:are|were)\s+no\s+tests?\b|"
    r"\btests?\s+skipped\b|"
    r"\bdid\s+not\s+run\s+tests?\b"
)
VALIDATION_SCAFFOLD = re.compile(
    r"(?i)^(?:results?|commands?|evidence|checks?|tests?|validation|verification):$"
)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
FENCED_CODE = re.compile(
    r"(?ms)^[ \t]*(?P<fence>`{3,}|~{3,})[^\n]*\n.*?^[ \t]*(?P=fence)[ \t]*$"
)
INLINE_CODE = re.compile(r"(?s)(?P<ticks>`+).*?(?P=ticks)")
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
    linkable_body = INLINE_CODE.sub("", FENCED_CODE.sub("", body))
    branch = str(pull_request.get("head", {}).get("ref") or "")
    if pull_request.get("draft"):
        failures.append("pull request must be ready for review, not draft")
    if not CONVENTIONAL_TITLE.fullmatch(title):
        failures.append("pull-request title is not conventional")
    if not body.strip():
        failures.append("pull-request body is empty")
    elif not (sections := validation_sections(body)):
        failures.append("pull-request body lacks a test or validation section")
    elif not any(meaningful_validation(section) for section in sections):
        failures.append("pull-request validation section has no verification evidence")
    issue_match = ISSUE_BRANCH.search(branch)
    if issue_match:
        issue_number = issue_match.group(1)
        base = pull_request.get("base", {})
        base_ref = str(base.get("ref") or "")
        default_branch = str(base.get("repo", {}).get("default_branch") or "")
        if not default_branch or base_ref != default_branch:
            expected = default_branch or "the repository default"
            failures.append(
                f"issue-backed pull request must target default branch {expected}"
            )
        linked = {match.group(1) for match in ISSUE_LINK.finditer(linkable_body)}
        if linked != {issue_number}:
            failures.append(
                f"issue-backed pull request must close only issue #{issue_number}"
            )
        elif issue_lookup is not None:
            issue_is_valid, issue_failure = issue_lookup(int(issue_number))
            if not issue_is_valid:
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
    if issue.get("state") != "open":
        return False, f"linked issue #{issue_number} is closed"
    return True, ""


def validation_sections(body: str) -> list[str]:
    sections: list[str] = []
    current: list[str] | None = None
    section_level = 0
    fence = ""

    for line in body.splitlines():
        stripped = line.lstrip()
        if fence:
            if re.fullmatch(rf"{re.escape(fence[0])}{{{len(fence)},}}\s*", stripped):
                fence = ""
            if current is not None:
                current.append(line)
            continue

        if fence_match := FENCE_MARKER.match(line):
            fence = fence_match.group("fence")
            if current is not None:
                current.append(line)
            continue

        heading = MARKDOWN_HEADING.match(line)
        if heading:
            level = len(heading.group("marks"))
            title = heading.group("title").strip().casefold()
            if current is not None and level <= section_level:
                sections.append("\n".join(current))
                current = None
            if current is None and title in VALIDATION_HEADINGS:
                current = []
                section_level = level
            elif current is not None:
                current.append(line)
            continue

        if current is not None:
            current.append(line)

    if current is not None:
        sections.append("\n".join(current))
    return sections


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
        if MARKDOWN_HEADING.fullmatch(stripped):
            continue
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
            if ISSUE_LINK.fullmatch(clause.rstrip(".,;:!?")):
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
