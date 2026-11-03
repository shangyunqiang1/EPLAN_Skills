"""Refresh provenance from explicitly checked-out upstream repos in .upstream/.

Review upstream commits, changes and license notices before running. This does
not download or update source files, and must not be used to hide local edits.
"""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/eplan-skills"
REPOS = ["eplan-mcp", "eplan-scripting-skill", "eec-pro-skill", "eplan-cloudflare-rags"]


def main():
    sources, files, integration_files = [], [], []
    for repo in REPOS:
        source = ROOT / ".upstream" / repo
        commit = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
        sources.append({"repository": f"https://github.com/Canary-ECAD/{repo}", "commit": commit, "license": "MIT", "copyright": "Copyright (c) 2025 Christian D. Lopez"})

    def record(repo, original, bundled):
        before = ROOT / ".upstream" / repo / original
        after = PLUGIN / bundled
        # Git checkouts differ in CRLF/LF conversion; these are all text files.
        digest = lambda path: hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        files.append({"source": repo, "upstreamPath": original, "path": bundled, "upstreamSha256": digest(before), "bundledSha256": digest(after)})

    for path in sorted((PLUGIN / "vendor/eplan-mcp").rglob("*")):
        if path.is_file() and not any(part in {"__pycache__", ".pytest_cache", "logs"} for part in path.parts):
            relative = path.relative_to(PLUGIN / "vendor/eplan-mcp").as_posix()
            if (ROOT / ".upstream/eplan-mcp" / relative).is_file():
                record("eplan-mcp", relative, "vendor/eplan-mcp/" + relative)
            else:
                integration_files.append({"path": "vendor/eplan-mcp/" + relative,
                    "sha256": hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()})
    for repo, upstream, bundled in [
        ("eplan-scripting-skill", "skills/eplan-p8/eplan-scripting", "skills/eplan-scripting"),
        ("eec-pro-skill", "skills/eec-pro-development", "skills/eec-pro-development"),
    ]:
        for path in sorted((PLUGIN / bundled).rglob("*")):
            if path.is_file():
                relative = path.relative_to(PLUGIN / bundled).as_posix()
                record(repo, upstream + "/" + relative, bundled + "/" + relative)
    record("eplan-scripting-skill", "router/SKILL.md", "skills/eplan-router/SKILL.md")
    for repo in REPOS:
        record(repo, "LICENSE", f"licenses/{repo}-MIT.txt")
    (PLUGIN / "upstream-lock.json").write_text(json.dumps({"hashNormalization": "text-crlf-to-lf", "sources": sources, "files": files, "integrationFiles": integration_files}, indent=2) + "\n", encoding="utf-8")
    print(f"Recorded {len(files)} upstream mappings. Review source and bundled hash differences.")


if __name__ == "__main__":
    main()
