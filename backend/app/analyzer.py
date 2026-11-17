"""Bounded, deterministic source checks for common risky coding patterns."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Finding:
    rule_id: str
    severity: str
    title: str
    file: str
    line: int
    evidence: str
    recommendation: str


RULES = [
    ("SEC001", "high", "Possible hard-coded credential", re.compile(r"""(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*["'][^"']{8,}["']"""), "Move the value to a secret manager or environment variable and rotate it if it was exposed."),
    ("SEC002", "high", "Dangerous dynamic evaluation", re.compile(r"\beval\s*\("), "Avoid evaluating untrusted strings. Use a parser or explicit allow-listed operations."),
    ("SEC003", "medium", "Potential unsafe HTML injection", re.compile(r"dangerouslySetInnerHTML|innerHTML\s*="), "Sanitize untrusted HTML or render text through framework escaping."),
    ("SEC004", "medium", "Disabled TLS certificate verification", re.compile(r"(?i)(verify\s*=\s*False|rejectUnauthorized\s*:\s*false)"), "Keep TLS certificate verification enabled outside isolated tests."),
    ("SEC005", "medium", "Potential SQL string concatenation", re.compile(r"""(?i)(execute|query)\s*\(\s*f["']|["'][^"']*\sSELECT\s+.+["']\s*\+"""), "Use parameterized queries rather than constructing SQL with string interpolation."),
    ("SEC006", "low", "Debug output may expose sensitive data", re.compile(r"console\.log\s*\(|print\s*\("), "Remove noisy debug output and ensure secrets or personal data are never logged."),
]


def analyze_files(files: list[dict]) -> list[dict]:
    findings: list[dict] = []
    for item in files:
        path = item["path"]
        content = item["content"]
        for line_number, line in enumerate(content.splitlines(), start=1):
            for rule_id, severity, title, pattern, recommendation in RULES:
                if pattern.search(line):
                    findings.append(Finding(
                        rule_id=rule_id,
                        severity=severity,
                        title=title,
                        file=path,
                        line=line_number,
                        evidence=line.strip()[:240],
                        recommendation=recommendation,
                    ).__dict__)
    return findings
