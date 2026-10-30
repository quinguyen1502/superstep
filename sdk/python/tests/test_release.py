"""install.sh and the shared server/CLI version (TASK-0156)."""
import os
import re
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
INSTALL = ROOT / "scripts" / "install.sh"


def _version_py() -> str:
    text = (ROOT / "sdk" / "python" / "src" / "superstep" / "_version.py").read_text(encoding="utf-8")
    match = re.search(r'__version__ = "([^"]+)"', text)
    assert match
    return match.group(1)


def _server_version() -> str:
    text = (ROOT / "backend" / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"', text, re.M)
    assert match
    return match.group(1)


def _install_default() -> str:
    text = INSTALL.read_text(encoding="utf-8")
    match = re.search(r'VERSION="\$\{SUPERSTEP_VERSION:-([^}]+)\}"', text)
    assert match
    return match.group(1)


def test_cli_server_and_installer_share_one_version():
    version = _version_py()
    assert version == _server_version() == _install_default() == "0.9.0"


def _env(home: Path, bin_dir: Path) -> dict:
    return {
        "HOME": str(home),
        "PATH": f"{bin_dir}{os.pathsep}/bin",
        "TMPDIR": str(home.parent),
        "SUPERSTEP_VERSION": "0.9.0",
    }


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def _run(home: Path, bin_dir: Path):
    return subprocess.run(
        ["sh", str(INSTALL)],
        env=_env(home, bin_dir),
        capture_output=True,
        text=True,
        check=False,
    )


def test_install_sh_with_uv_installs_the_extra(tmp_path):
    home = tmp_path / "home"
    bin_dir = tmp_path / "bin"
    home.mkdir()
    bin_dir.mkdir()
    _write(
        bin_dir / "uv",
        "#!/bin/sh\n"
        "printf '%s\\n' \"$*\" >> \"$HOME/uv-args\"\n"
        "if [ \"$1\" = tool ]; then\n"
        "  mkdir -p \"$HOME/.local/bin\"\n"
        "  printf '%s\\n' '#!/bin/sh' 'exit 0' > \"$HOME/.local/bin/superstep\"\n"
        "  chmod +x \"$HOME/.local/bin/superstep\"\n"
        "fi\n"
        "exit 0\n",
    )
    proc = _run(home, bin_dir)
    assert proc.returncode == 0, proc.stderr
    assert "superstep[cli]==0.9.0" in (home / "uv-args").read_text(encoding="utf-8")
    assert (home / ".local" / "bin" / "superstep").is_file()
    assert not (home / "uv-installer-ran").exists()
    assert "WSL" not in proc.stderr


def test_install_sh_without_python_or_uv_installs_uv(tmp_path):
    home = tmp_path / "home"
    bin_dir = tmp_path / "bin"
    home.mkdir()
    bin_dir.mkdir()
    _write(
        bin_dir / "curl",
        "#!/bin/sh\n"
        "cat <<'EOF'\n"
        "#!/bin/sh\n"
        "mkdir -p \"$HOME/.local/bin\"\n"
        "cat > \"$HOME/.local/bin/uv\" <<'UV'\n"
        "#!/bin/sh\n"
        "printf '%s\\n' \"$*\" >> \"$HOME/uv-args\"\n"
        "if [ \"$1\" = tool ]; then\n"
        "  mkdir -p \"$HOME/.local/bin\"\n"
        "  printf '%s\\n' '#!/bin/sh' 'exit 0' > \"$HOME/.local/bin/superstep\"\n"
        "  chmod +x \"$HOME/.local/bin/superstep\"\n"
        "fi\n"
        "exit 0\n"
        "UV\n"
        "chmod +x \"$HOME/.local/bin/uv\"\n"
        ": > \"$HOME/uv-installer-ran\"\n"
        "EOF\n",
    )
    proc = _run(home, bin_dir)
    assert proc.returncode == 0, proc.stderr
    assert (home / "uv-installer-ran").is_file()
    assert "superstep[cli]==0.9.0" in (home / "uv-args").read_text(encoding="utf-8")
    assert (home / ".local" / "bin" / "superstep").is_file()


def test_install_sh_refuses_native_windows(tmp_path):
    home = tmp_path / "home"
    bin_dir = tmp_path / "bin"
    home.mkdir()
    bin_dir.mkdir()
    _write(bin_dir / "uname", "#!/bin/sh\nprintf '%s\\n' MINGW64_NT-10.0\n")
    proc = _run(home, bin_dir)
    assert proc.returncode != 0
    assert "WSL" in proc.stderr
    assert not (home / "uv-args").exists()


def test_handbook_cli_pages_share_heading_levels():
    def levels(path: Path) -> list[int]:
        found = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.startswith("#"):
                continue
            marks = len(line) - len(line.lstrip("#"))
            if marks and line[marks:marks + 1] == " ":
                found.append(marks)
        return found

    en = ROOT / "handbook" / "docs" / "en" / "operate" / "cli.md"
    vi = ROOT / "handbook" / "docs" / "vi" / "operate" / "cli.md"
    assert levels(en) == levels(vi) == [1, 2, 2, 2, 2]
    for nav in (ROOT / "handbook" / "mkdocs.yml", ROOT / "handbook" / "mkdocs.vi.yml"):
        assert "operate/cli.md" in nav.read_text(encoding="utf-8")
