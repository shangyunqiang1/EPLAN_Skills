"""Offline package checks. Install requirements-dev.txt before running."""
from pathlib import Path
import hashlib
import json
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/eplan-skills"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate():
    manifest = read_json(PLUGIN / "plugin.json")
    assert manifest["$schema"] == "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
    assert manifest["name"] == "eplan-skills"
    assert re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"])
    interface = manifest["extensions"]["com.openai"]["interface"]
    assert len(interface["shortDescription"]) <= 30
    assert interface["category"] == "Developer Tools"
    for relative in [".codex-plugin/plugin.json", ".claude-plugin/plugin.json"]:
        legacy = read_json(PLUGIN / relative)
        for field in ["name", "version", "author", "license"]:
            assert legacy[field] == manifest[field], (relative, field)
    names = []
    for path in sorted((PLUGIN / "skills").glob("*/SKILL.md")):
        text = path.read_text(encoding="utf-8")
        assert text.startswith("---\n"), path
        metadata = yaml.safe_load(text.split("---", 2)[1])
        assert metadata["name"] == path.parent.name
        assert isinstance(metadata["description"], str) and metadata["description"].strip()
        names.append(metadata["name"])
    assert len(names) == len(set(names)) == 4, names
    for path in (PLUGIN / "skills").rglob("*.md"):
        for link in re.findall(r"\]\(([^\s)]+)\)", path.read_text(encoding="utf-8")):
            if "://" in link or link.startswith("#"):
                continue
            target = (path.parent / link.split("#")[0]).resolve()
            assert target.is_relative_to(PLUGIN) and target.exists(), (path, link)
    onboarding = manifest["extensions"]["com.openai"]["onboardingSkill"]
    assert (PLUGIN / onboarding).is_file()
    portable = read_json(PLUGIN / "mcp.json")
    assert portable["$schema"] == "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"
    servers = portable["mcpServers"]
    assert set(servers) == {"eplan", "eplan-rag", "eplan-wiki-2027", "eecpro-rag"}
    assert servers["eplan"]["args"] == ["${PLUGIN_ROOT}/scripts/run_mcp.py"]
    for filename, variable in [(".mcp.json", "${PLUGIN_ROOT}"), ("mcp-claude.json", "${CLAUDE_PLUGIN_ROOT}")]:
        legacy = read_json(PLUGIN / filename)["mcpServers"]
        assert legacy["eplan"]["args"] == [variable + "/scripts/run_mcp.py"]
        assert set(legacy) == set(servers)
        for name in set(servers) - {"eplan"}:
            assert legacy[name]["url"] == servers[name]["url"]
            assert legacy[name]["type"] == "http"
    marketplace = read_json(ROOT / ".agents/plugins/marketplace.json")
    entry, = marketplace["plugins"]
    assert (ROOT / entry["source"]["path"]).resolve() == PLUGIN.resolve()
    assert entry["name"] == marketplace["name"] == manifest["name"]
    for name in ["LICENSE", "THIRD_PARTY_NOTICES.md"]:
        assert (ROOT / name).read_bytes() == (PLUGIN / name).read_bytes()
    lock = read_json(PLUGIN / "upstream-lock.json")
    assert len(lock["sources"]) == 4
    for item in lock["files"]:
        path = PLUGIN / item["path"]
        assert hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() == item["bundledSha256"], path
    for path in PLUGIN.rglob("*"):
        assert not path.is_symlink(), path
        if path.is_file():
            assert path.suffix.lower() not in {".dll", ".pfx", ".key", ".pem", ".epdz", ".elk"}, path
            assert path.name != ".env", path
    print(f"Validated {len(names)} skills, {len(servers)} MCP servers, {len(lock['files'])} attributed upstream files.")


if __name__ == "__main__":
    validate()
