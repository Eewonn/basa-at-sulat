"""Fail if the code we ship could reach the internet.

    python scripts/offline_audit.py

Looks at the Python in engine/app, ai and scripts (tests excluded) for URLs whose host isn't this laptop and
for imports of network client libraries. It is a tripwire for the "everything runs offline" claim, not a
proof: the tests also refuse non-local connections (scripts/netguard.py).
"""

import ast
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDITED = ("engine/app", "ai", "scripts")
SKIPPED_PARTS = {"tests", ".venv", "node_modules", "__pycache__", "models"}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
FORBIDDEN_IMPORTS = {
    "requests", "httpx", "aiohttp", "urllib3", "websockets", "websocket", "ftplib", "smtplib",
    "poplib", "imaplib", "telnetlib", "paramiko", "pycurl", "grpc",
}
URL = re.compile(r"https?" + r"://[^\s\"'<>`)]+")
# The one pattern that is allowed to look like a URL: the engine's CORS rule, which admits only local pages.
LOCAL_ORIGIN_PATTERN = "http" + r"://(localhost|127\.0\.0\.1)"


def python_files(root: Path):
    for folder in AUDITED:
        for path in sorted((root / folder).rglob("*.py")):
            if not SKIPPED_PARTS.intersection(path.relative_to(root).parts):
                yield path


def find_problems(root: Path = REPO_ROOT) -> list[str]:
    problems = []
    for path in python_files(root):
        shown = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        for number, line in enumerate(text.splitlines(), 1):
            for match in URL.finditer(line):
                if line[match.start():].startswith(LOCAL_ORIGIN_PATTERN):
                    continue
                host = urlparse(match.group()).hostname
                if host is not None and host not in LOCAL_HOSTS:
                    problems.append(f"{shown}:{number}: URL to {host} ({match.group()})")
        try:
            tree = ast.parse(text)
        except SyntaxError as err:
            problems.append(f"{shown}:{err.lineno}: could not parse, so it was not audited ({err.msg})")
            continue
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                if name.split(".")[0] in FORBIDDEN_IMPORTS:
                    problems.append(f"{shown}:{node.lineno}: imports the network library '{name}'")
    return problems


def main() -> int:
    problems = find_problems()
    if problems:
        print("Code that could reach the internet:")
        for problem in problems:
            print(f"  {problem}")
        return 1
    print("No outbound URLs or network client libraries in engine/app, ai or scripts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
