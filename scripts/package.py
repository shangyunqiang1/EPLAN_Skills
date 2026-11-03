"""Validate and create one self-contained plugin archive (no marketplace)."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/eplan-skills"


def package() -> Path:
    subprocess.run([sys.executable, str(ROOT / "scripts/validate.py")], check=True)
    version = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))["version"]
    output = ROOT / "dist" / f"eplan-skills-{version}.zip"
    output.parent.mkdir(exist_ok=True)
    expected = []
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(PLUGIN.rglob("*")):
            relative = path.relative_to(PLUGIN)
            if any(p in {"__pycache__", ".pytest_cache", "logs", ".git"} for p in relative.parts):
                continue
            if path.is_file() and path.suffix not in {".pyc", ".pyo", ".log"}:
                if path.is_symlink():
                    raise ValueError(f"Symlink in package: {relative}")
                expected.append(relative.as_posix())
                archive.write(path, relative.as_posix())
    with zipfile.ZipFile(output) as archive:
        assert sorted(archive.namelist()) == sorted(expected)
        assert archive.testzip() is None
        assert "plugin.json" in expected and "mcp.json" in expected
        for name in expected:
            assert archive.read(name) == (PLUGIN / name).read_bytes()
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(".zip.sha256").write_text(f"{digest}  {output.name}\n", encoding="utf-8")
    print(f"Archive verified: {output} ({len(expected)} files, SHA256 {digest})")
    return output


if __name__ == "__main__":
    package()
