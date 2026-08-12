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
ISSUE_LINK = re.compile(
    r"(?i)\b(?P<keyword>close(?:s|d)?|fix(?:es|ed)?|resolve(?:s|d)?):?[ \t]+"
    r"(?:(?P<repository>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+))?"
    r"#(?P<number>\d+)\b"
)
VALIDATION_HEADINGS = {
    "test",
    "test plan",
    "testing",
    "tests",
    "validation",
    "verification",
}
MARKDOWN_HEADING = re.compile(
    r"^ {0,3}(?P<marks>#{1,6})(?:[ \t]+(?P<title>.*?)(?:[ \t]+#+)?[ \t]*|[ \t]*)$"
)
MARKDOWN_SETEXT_UNDERLINE = re.compile(r"^ {0,3}(?P<marks>=+|-+)[ \t]*$")
FENCE_MARKER = re.compile(
    r"^(?P<indent> {0,3})(?P<fence>`{3,}|~{3,})(?P<info>.*)$"
)
NEGATIVE_VALIDATION = re.compile(
    r"(?i)(?:^|:\s*)(?:n/?a|none|not applicable|not required|not run|"
    r"not tested|pending|skipped|todo)(?:\b|[.!])|"
    r"\b(?:not|never|did\s+not|didn't)\s+"
    r"(?:complete(?:d)?|pass(?:ed)?|verif(?:y|ied)|succeed(?:ed)?|successful(?:ly)?)\b|"
    r"\btests?\s+(?:were\s+|was\s+)?not\s+(?:run|tested)\b|"
    r"\bno\s+tests?\s+(?:were\s+)?(?:run|required|needed)\b|"
    r"\bthere\s+(?:are|were)\s+no\s+tests?\b|"
    r"\btests?\s+(?:(?:was|were)\s+)?skipped\b|"
    r"\bdid\s+not\s+run\s+tests?\b|"
    r"\b(?:failed|failing)\b|"
    r"\bexit(?:ed)?\s+with\s+(?:code\s+)?[1-9]\d*\b|"
    r"\bnon[- ]?zero\b|"
    r"\b(?:pending|todo)\b"
)
HARD_FAILURE_VALIDATION = re.compile(
    r"(?i)\b(?:failed|failing)\b|"
    r"\bexit(?:ed)?\s+with\s+(?:code\s+)?[1-9]\d*\b|"
    r"\bnon[- ]?zero\b|"
    r"\b(?:pending|todo)\b"
)
VALIDATION_SCAFFOLD = re.compile(
    r"(?i)^(?:(?:results?|commands?|evidence|checks?|tests?|validation|verification):|"
    r"how was this tested\?)$"
)
POSITIVE_VALIDATION = re.compile(
    r"(?i)\b(?:pass(?:ed|es)?|verif(?:ied|ies)|succeed(?:ed|s)?|successful(?:ly)?|"
    r"completed?)\b"
)
HTML_COMMENT = re.compile(r"<!--.*?(?:-->|$)", re.DOTALL)
THEMATIC_BREAK = re.compile(
    r"^(?:(?:\*[ \t]*){3,}|(?:-[ \t]*){3,}|(?:_[ \t]*){3,})$"
)
PRESENTATION_MARKUP = re.compile(r"(?<!\\)[*_~]+")
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
    linkable_body = strip_inline_code(strip_indented_code(strip_fenced_code(body)))
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
    issue_links = list(ISSUE_LINK.finditer(linkable_body))
    non_fixes_links = [
        match for match in issue_links if match.group("keyword").casefold() != "fixes"
    ]
    linked = {
        match.group("number")
        for match in issue_links
        if match.group("repository") is None
    }
    qualified_links = {
        (match.group("repository"), match.group("number"))
        for match in issue_links
        if match.group("repository") is not None
    }
    if issue_match:
        issue_number = issue_match.group(1)
        if linked != {issue_number} or qualified_links or non_fixes_links:
            failures.append(
                f"issue-backed pull request must close only issue #{issue_number}"
            )
        else:
            validate_linked_issue(
                pull_request, int(issue_number), issue_lookup, failures
            )
    elif issue_links:
        if len(linked) == 1 and not qualified_links:
            issue_number = next(iter(linked))
            failures.append(
                f"issue-backed pull request branch must include issue #{issue_number}"
            )
        else:
            failures.append("issue-backed pull request branch must include its issue number")
        if non_fixes_links:
            failures.append("pull request must use the exact Fixes #N issue reference")
    return failures


def validate_linked_issue(
    pull_request: dict[str, Any],
    issue_number: int,
    issue_lookup: IssueLookup | None,
    failures: list[str],
) -> None:
    base = pull_request.get("base", {})
    base_ref = str(base.get("ref") or "")
    default_branch = str(base.get("repo", {}).get("default_branch") or "")
    if not default_branch or base_ref != default_branch:
        expected = default_branch or "the repository default"
        failures.append(
            f"issue-backed pull request must target default branch {expected}"
        )
    if issue_lookup is not None:
        issue_is_valid, issue_failure = issue_lookup(issue_number)
        if not issue_is_valid:
            failures.append(issue_failure)


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


def validation_sections(body: str) -> list[str]:
    sections: list[str] = []
    current: list[str] | None = None
    section_level = 0
    fence = ""
    lines = body.splitlines()
    index = 0

    while index < len(lines):
        line = lines[index]
        if fence:
            if is_closing_fence(line, fence):
                fence = ""
            if current is not None:
                current.append(line)
            index += 1
            continue

        if opening := opening_fence(line):
            fence = opening
            if current is not None:
                current.append(line)
            index += 1
            continue

        heading = markdown_heading(lines, index)
        if heading is not None:
            level, title, consumed = heading
            if current is not None and level <= section_level:
                sections.append("\n".join(current))
                current = None
            if current is None and title in VALIDATION_HEADINGS:
                current = []
                section_level = level
            elif current is not None:
                current.extend(lines[index : index + consumed])
            index += consumed
            continue

        if current is not None:
            current.append(line)
        index += 1

    if current is not None:
        sections.append("\n".join(current))
    return sections


def markdown_heading(lines: list[str], index: int) -> tuple[int, str, int] | None:
    """Parse an ATX or Setext heading outside fenced code."""
    line = lines[index]
    if atx := MARKDOWN_HEADING.fullmatch(line):
        title = (atx.group("title") or "").strip().casefold()
        return len(atx.group("marks")), title, 1
    if index + 1 >= len(lines) or not line.strip():
        return None
    if setext := MARKDOWN_SETEXT_UNDERLINE.fullmatch(lines[index + 1]):
        level = 1 if setext.group("marks").startswith("=") else 2
        return level, line.strip().casefold(), 2
    return None


def strip_fenced_code(body: str) -> str:
    visible: list[str] = []
    fence_character = ""
    fence_length = 0

    for line in body.splitlines(keepends=True):
        if fence_character:
            if is_closing_fence(line.rstrip("\r\n"), fence_character * fence_length):
                fence_character = ""
                fence_length = 0
            continue

        if fence := opening_fence(line.rstrip("\r\n")):
            fence_character = fence[0]
            fence_length = len(fence)
            continue

        visible.append(line)

    return "".join(visible)


def strip_indented_code(body: str) -> str:
    """Remove conservatively detected indented code from closing-link input."""
    visible: list[str] = []
    for line in body.splitlines(keepends=True):
        if line.startswith("    ") or line.startswith("\t"):
            visible.append("\uFFFC\n" if line.endswith(("\n", "\r")) else "\uFFFC")
        else:
            visible.append(line)
    return "".join(visible)


def opening_fence(line: str) -> str | None:
    """Return a valid top-level Markdown fence opener, if present."""
    match = FENCE_MARKER.fullmatch(line)
    if match is None:
        return None
    fence = match.group("fence")
    if fence.startswith("`") and "`" in match.group("info"):
        return None
    return fence


def is_closing_fence(line: str, opening: str) -> bool:
    """Recognize a matching Markdown fence closer with valid indentation."""
    return bool(
        re.fullmatch(
            rf" {{0,3}}{re.escape(opening[0])}{{{len(opening)},}}[ \t]*",
            line,
        )
    )


def strip_inline_code(text: str) -> str:
    """Remove well-formed Markdown code spans in linear time."""
    runs: list[tuple[int, int, int, bool]] = []
    index = 0
    while index < len(text):
        if text[index] != "`":
            index += 1
            continue
        end = index + 1
        while end < len(text) and text[end] == "`":
            end += 1
        runs.append((index, end, end - index, is_escaped(text, index)))
        index = end

    next_same_length: list[int | None] = [None] * len(runs)
    latest_by_length: dict[int, int] = {}
    for run_index in range(len(runs) - 1, -1, -1):
        length = runs[run_index][2]
        next_same_length[run_index] = latest_by_length.get(length)
        latest_by_length[length] = run_index

    visible: list[str] = []
    cursor = 0
    run_index = 0
    while run_index < len(runs):
        if runs[run_index][3]:
            run_index += 1
            continue
        closer_index = next_same_length[run_index]
        if closer_index is None:
            run_index += 1
            continue
        visible.append(text[cursor : runs[run_index][0]])
        visible.append("\uFFFC")
        cursor = runs[closer_index][1]
        run_index = closer_index + 1
    visible.append(text[cursor:])
    return "".join(visible)


def is_escaped(text: str, index: int) -> bool:
    backslashes = 0
    cursor = index - 1
    while cursor >= 0 and text[cursor] == "\\":
        backslashes += 1
        cursor -= 1
    return backslashes % 2 == 1


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
    normalized_content = PRESENTATION_MARKUP.sub("", content)
    if HARD_FAILURE_VALIDATION.search(normalized_content):
        return False
    for line in content.splitlines():
        if re.fullmatch(r"(?:[-+*]|\d+[.)])", line.strip()):
            continue
        stripped = re.sub(
            r"^(?:[-+*]|\d+[.)])\s+", "", line.strip()
        ).strip()
        if MARKDOWN_HEADING.fullmatch(stripped):
            continue
        if THEMATIC_BREAK.fullmatch(stripped):
            continue
        if opening_fence(stripped):
            continue
        if re.match(r"^\[\s\]", stripped):
            continue
        stripped = re.sub(r"^\[[ xX]\]\s*", "", stripped)
        stripped = PRESENTATION_MARKUP.sub("", stripped).strip()
        for clause in stripped.split(";"):
            if clause_has_validation_evidence(clause):
                return True
    return False


def clause_has_validation_evidence(clause: str) -> bool:
    """Evaluate a semicolon-delimited validation clause and contrast tail."""
    clause = clause.strip()
    if not clause:
        return False
    if ISSUE_LINK.fullmatch(clause.rstrip(".,;:!?")):
        return False
    if VALIDATION_SCAFFOLD.fullmatch(clause):
        return False
    negative = NEGATIVE_VALIDATION.search(clause)
    if negative is None:
        return True
    if POSITIVE_VALIDATION.search(clause[: negative.start()]):
        return True
    tail = clause[negative.end() :]
    contrast = re.match(
        r"(?i)^\s*,?\s*(?:but|however|instead)\b[\s,:-]*(.+)$",
        tail,
    )
    return bool(contrast and clause_has_validation_evidence(contrast.group(1)))


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
