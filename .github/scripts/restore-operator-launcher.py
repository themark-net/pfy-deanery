#!/usr/bin/env python3
"""Restore scripts/pfy if truncated/emptied; drop cargo/pywebview launch one-liners."""
from pathlib import Path
import os
import urllib.request

MAIN = "22a2f2448f9565643ac1b62fa5f9c6026547eb1a"
URL = f"https://raw.githubusercontent.com/themark-net/pfy-deanery/{MAIN}/scripts/pfy"
OLD_LAUNCH = (
    '    echo "native window (pywebview)"\n'
    '    echo "  one-liner: cd gui/operator/src-tauri && cargo build --release"\n'
    '    exec python3 "$ROOT/scripts/pfy-gui.py"\n'
)
NEW_LAUNCH = (
    '    # pfy-gui.py prints native window (webkit|tk); never a cargo/pip/apt one-liner\n'
    '    exec python3 "$ROOT/scripts/pfy-gui.py"\n'
)
OLD_DIE = '  die "native GUI missing (scripts/pfy-gui.py)"\n'
NEW_DIE = (
    '  mkdir -p "$STATE_DIR"\n'
    '  art="$STATE_DIR/gui-stopped-exit.txt"\n'
    '  printf \'STOPPED_EXIT\\nerror: scripts/pfy-gui.py missing\\n\' >"$art"\n'
    '  echo "STOPPED_EXIT: scripts/pfy-gui.py missing" >&2\n'
    '  echo "artifact: $art" >&2\n'
    '  exit 1\n'
)
REPLACES = [
    (
        "Native window is the main interface (Tauri if built, else pywebview / webkit / tkinter).\n",
        "Native window is the main interface. Tauri if pfy-operator exists; else webkit or stdlib tk.\n",
    ),
    (
        "Native window is the main interface. Tauri binary (when built):\n"
        "  cd gui/operator/src-tauri && cargo build --release\n"
        "  \u2192 gui/operator/src-tauri/target/release/pfy-operator\n"
        "Else pywebview + WebKitGTK (scripts/pfy-gui.py). Missing pywebview: install tip, exit 2.\n",
        "Native window is the main interface. Tauri when\n"
        "  gui/operator/src-tauri/target/{release,debug}/pfy-operator exists.\n"
        "Else already-on-box webkit or stdlib tk (scripts/pfy-gui.py). Window always opens.\n",
    ),
    (
        "  pfy board [--open]      alias of the native operator window (Tauri if built, else pywebview)\n",
        "  pfy board [--open]      alias of the native operator window (Tauri / webkit / tk)\n",
    ),
]
STOPPED_FN = (
    "def stopped_exit(error):\n"
    "    state = Path(os.environ.get(\"PFY_STATE_DIR\", str(Path.home() / \".pfy-mentat\")))\n"
    "    state.mkdir(parents=True, exist_ok=True)\n"
    "    artifact = state / \"gui-stopped-exit.txt\"\n"
    "    artifact.write_text(f\"STOPPED_EXIT\\nerror: {error}\\n\", encoding=\"utf-8\")\n"
    "    print(f\"STOPPED_EXIT: {error}\", file=sys.stderr)\n"
    "    print(f\"artifact: {artifact}\", file=sys.stderr)\n"
    "    return 1\n\n"
)


def broken(text: str) -> bool:
    if "print_live_models" not in text:
        return True
    if 'main "$@"' not in text:
        return True
    if "cmd_status()" not in text:
        return True
    return False


def patch_gui() -> None:
    p = Path("scripts/pfy-gui.py")
    if not p.exists():
        return
    t = p.read_text(encoding="utf-8")
    if "def stopped_exit" not in t:
        needle = "def load_board():"
        if needle in t:
            t = t.replace(needle, STOPPED_FN + needle, 1)
            print("inserted stopped_exit in pfy-gui.py")
    t = t.replace(
        'print(f"error: native window could not open: {e}", file=sys.stderr); return 1',
        "return stopped_exit(str(e))",
        1,
    )
    t = t.replace(
        'print("error: native window could not open", file=sys.stderr); return 1',
        'return stopped_exit("no already-on-box toolkit opened a native window")',
        1,
    )
    # spec print is native window (tk), never tkinter
    t = t.replace('print("native window (tkinter)", flush=True)', 'print("native window (tk)", flush=True)')
    p.write_text(t, encoding="utf-8")


def main() -> None:
    p = Path("scripts/pfy")
    t = p.read_text(encoding="utf-8") if p.exists() else ""
    if not p.exists() or broken(t):
        print("scripts/pfy truncated/broken — restoring from", MAIN)
        p.write_bytes(urllib.request.urlopen(URL, timeout=30).read())
        t = p.read_text(encoding="utf-8")
    if OLD_LAUNCH in t:
        t = t.replace(OLD_LAUNCH, NEW_LAUNCH, 1)
        print("dropped cargo/pywebview launch one-liners")
    if OLD_DIE in t:
        t = t.replace(OLD_DIE, NEW_DIE, 1)
        print("STOPPED_EXIT when pfy-gui.py missing")
    for old, new in REPLACES:
        if old in t:
            t = t.replace(old, new, 1)
            print("replaced usage block")
    p.write_text(t, encoding="utf-8")
    if broken(p.read_text(encoding="utf-8")):
        raise SystemExit("scripts/pfy still truncated after restore")
    print("scripts/pfy bytes", p.stat().st_size)
    patch_gui()


if __name__ == "__main__":
    main()
