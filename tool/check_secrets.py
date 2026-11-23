#!/usr/bin/env python3
"""Fails the build if a signing key, keystore, service-account file or an
obvious API secret has been committed. Runs first in CI (no network)."""
import os
import re
import sys

SKIP_DIRS = {".git", ".dart_tool", "build", ".pub-cache", "node_modules"}
BAD_FILES = re.compile(
    r"(\.jks|\.keystore|\.p12|\.p8|\.mobileprovision|key\.properties|google-services\.json|"
    r"GoogleService-Info\.plist|service[-_]account.*\.json|\.env)$",
    re.I,
)
PATTERNS = [
    ("private key", re.compile(r"-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----")),
    ("Google API key", re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("GitHub token", re.compile(r"gh[pousr]_[0-9A-Za-z]{36,}")),
    ("Slack token", re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}")),
    ("Stripe live key", re.compile(r"sk_live_[0-9A-Za-z]{20,}")),
]


def main():
    problems = []
    for base, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            path = os.path.join(base, f)
            if BAD_FILES.search(f):
                problems.append(f"{path}: secret file must not be committed")
                continue
            if os.path.getsize(path) > 2_000_000:
                continue
            try:
                text = open(path, encoding="utf-8").read()
            except (UnicodeDecodeError, OSError):
                continue
            for name, rx in PATTERNS:
                if rx.search(text) and not path.endswith("check_secrets.py"):
                    problems.append(f"{path}: looks like a {name}")
    if problems:
        print("\n".join(problems))
        sys.exit(1)
    print("no committed secrets found")


if __name__ == "__main__":
    main()
