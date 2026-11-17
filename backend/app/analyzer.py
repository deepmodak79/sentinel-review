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
    ("SEC001", "high", "Possible hard-coded credential", re.compile(r"""(?i)(api[_-]?key|secret|password|token|client_secret)\\s*[:=]\\s*["'][^"']{8,}["']"""), "Move the value to a secret manager or environment variable, rotate it if exposed, and remove it from repository history."),
    ("SEC002", "high", "Dangerous dynamic evaluation", re.compile(r"\\beval\\s*\\("), "Avoid evaluating untrusted strings. Use a parser or explicit allow-listed operations."),
    ("SEC003", "medium", "Potential unsafe HTML injection", re.compile(r"dangerouslySetInnerHTML|innerHTML\\s*="), "Sanitize untrusted HTML or render text through framework escaping."),
    ("SEC004", "medium", "Disabled TLS certificate verification", re.compile(r"(?i)(verify\\s*=\\s*False|rejectUnauthorized\\s*:\\s*false)"), "Keep TLS certificate verification enabled outside isolated tests."),
    ("SEC005", "high", "Potential SQL string interpolation", re.compile(r"""(?is)(?:execute|executemany|query)\\s*\\(\\s*(?:f["']|["'][^"']*\\sSELECT\\s+.+["']\\s*\\+)"""), "Use parameterized queries rather than constructing SQL with string interpolation."),
    ("SEC006", "low", "Debug output may expose sensitive data", re.compile(r"console\\.log\\s*\\(|print\\s*\\("), "Remove noisy debug output and ensure secrets or personal data are never logged."),
    ("SEC007", "high", "Subprocess invoked with shell=True", re.compile(r"subprocess\\.(?:run|Popen|call|check_output)\\s*\\([^)]*shell\\s*=\\s*True", re.S), "Pass an argument array with shell=False and validate each argument."),
    ("SEC008", "high", "Unsafe pickle deserialization", re.compile(r"\\bpickle\\.(?:loads|load)\\s*\\("), "Never unpickle untrusted input. Prefer JSON or another data-only serialization format."),
    ("SEC009", "medium", "Potential unsafe YAML loader", re.compile(r"\\byaml\\.load\\s*\\([^,)]*\\)"), "Use yaml.safe_load or explicitly pass yaml.SafeLoader."),
    ("SEC010", "medium", "Wildcard CORS origin", re.compile(r"""(?i)(?:allow_origins\\s*=\\s*\\[\\s*["']\\*["']|Access-Control-Allow-Origin["']?\\s*[:=]\\s*["']\\*["'])"""), "Allow only trusted application origins; avoid wildcard origins for sensitive APIs."),
]

SECRET_VALUE = re.compile(r"""(?i)((?:api[_-]?key|secret|password|token|client_secret|aws_secret_access_key|private_key|access_token|refresh_token)\\s*[:=]\\s*["'])[^"']+(["'])""")


def redact_evidence(value: str) -> str:
    """Never echo credential values back into the browser or API response."""
    return SECRET_VALUE.sub(r"\\1[REDACTED]\\2", value)


def analyze_files(files: list[dict]) -> list[dict]:
    findings: list[dict] = []
    for item in files:
        path = item["path"]
        content = item["content"]
        if not isinstance(content, str) or path.endswith((".lock", ".min.js", ".map")):
            continue
        for line_number, line in enumerate(content.splitlines(), start=1):
            for rule_id, severity, title, pattern, recommendation in RULES:
                if pattern.search(line):
                    findings.append(Finding(
                        rule_id=rule_id,
                        severity=severity,
                        title=title,
                        file=path,
                        line=line_number,
                        evidence=redact_evidence(line.strip()[:240]),
                        recommendation=recommendation,
                    ).__dict__)
    return findings
