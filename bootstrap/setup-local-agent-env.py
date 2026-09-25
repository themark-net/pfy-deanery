#!/usr/bin/env python3
"""
Centralized idempotent local agent environment check for pfy-mentat.

Authoritative operator path (ADR-0002, ADR-0010, T-0045/T-0047):
  Grok Build CLI + agent-cage (+ optional host Ollama/LiteLLM)

This script is a **health / guidance** helper. Prefer Make targets for real work:
  make cage-grok | cage-grok-net-smoke | cage-grok-ready | eval-v02

AgenC is catalog-only (ADR-0010) — not invoked or installed here.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_MD = REPO_ROOT / "AGENTS.md"
LOOP_DIR = REPO_ROOT / "integration" / "agenc" / "skills" / "loop-engineering"
GROK_BOOTSTRAP = REPO_ROOT / "bootstrap" / "grok-cli"
CAGE_MAKE = REPO_ROOT / "harness" / "agent-cage" / "Makefile"

DEFAULT_COMPONENTS = [
    "operator_path",
    "grok_bootstrap",
    "agent_cage",
    "loop_engineering_pack",
    "eval_harness",
    "memory_notes",
    "hermes_patterns",
    "safety_notes",
    "inference_notes",
]


def run(cmd: list[str], check: bool = False) -> subprocess.CompletedProcess:
    print(f"[RUN] {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


def have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def setup_operator_path() -> None:
    print("\n=== Operator path (authoritative) ===")
    print("Primary: Grok Build CLI (ADR-0002)")
    print("Lab:     agent-cage with make cage-grok / cage-grok-run / cage-grok-resume")
    print("Not:     AgenC as primary (ADR-0010 demoted; T-0046 re-eval later)")
    print("Docs:    docs/ops/DEPLOY.md, harness/agent-cage/overlays/grok/README.md")


def setup_grok_bootstrap() -> None:
    print("\n=== Grok CLI bootstrap package ===")
    if not GROK_BOOTSTRAP.is_dir():
        print(f"[WARN] missing {GROK_BOOTSTRAP}")
        return
    install = GROK_BOOTSTRAP / "install.sh"
    print(f"Present: {GROK_BOOTSTRAP}")
    print(f"Install: bash {install}   # optional --with-codebase-memory")
    if have("grok"):
        r = run(["grok", "--version"])
        print(f"Host grok: {(r.stdout or r.stderr or '').strip() or 'ok'}")
    else:
        print("[INFO] grok not on PATH — install Grok Build CLI on host first")


def setup_agent_cage() -> None:
    print("\n=== agent-cage lab ===")
    if not CAGE_MAKE.is_file():
        print(f"[WARN] missing {CAGE_MAKE}")
        return
    print("Targets: make cage-doctor | cage-init | cage-grok | cage-grok-net-smoke")
    print("Sessions: ~/.agentcage/grok-state/sessions (T-0047)")
    if have("docker"):
        r = run(
            [
                "docker",
                "inspect",
                "agent-cage-agent",
                "--format",
                "{{.State.Status}} {{.Config.Image}}",
            ]
        )
        if r.returncode == 0:
            print(f"Container: {r.stdout.strip()}")
        else:
            print("[INFO] agent-cage-agent not running — make cage-grok when needed")
    else:
        print("[WARN] docker not on PATH")


def setup_loop_engineering_pack() -> None:
    print("\n=== Loop Engineering skill pack (docs under integration/agenc/) ===")
    LOOP_DIR.mkdir(parents=True, exist_ok=True)
    roadmap = LOOP_DIR / "14-step-roadmap.md"
    if roadmap.is_file():
        print(f"Present: {roadmap}")
    else:
        print(f"[INFO] missing {roadmap} — restore from git or scoring-summary Entry 018/021")
    print("Note: path is historical (agenc/ folder name); content is Grok-usable docs, not AgenC runtime.")


def setup_eval_harness() -> None:
    print("\n=== Eval harness ===")
    ex = REPO_ROOT / "examples" / "eval-harness"
    if ex.is_dir():
        print(f"Present: {ex}")
        print("Run: make eval-tier0 | eval-v02 | eval-matrix")
    else:
        print("[WARN] examples/eval-harness missing")


def setup_memory_notes() -> None:
    print("\n=== Memory / RAG (S-tier watch from scoring-summary) ===")
    print("  - codebase-memory-mcp (lab smoke: make smoke-codebase-memory)")
    print("  - repowise (make smoke-repowise)")
    print("  - LEANN / Memvid / opencode-mem — catalogued; not auto-installed here")
    print("See docs/scoring-summary.md Cluster 2.")


def setup_hermes_patterns() -> None:
    print("\n=== Hermes-style feedback loops (pattern, not runtime install) ===")
    print("  1. Auto-memory → durable notes (TODO/OQ/session briefs)")
    print("  2. Auto-skill → first-party skills under bootstrap/grok-cli/skills/")
    print("  3. Curator → /ponytail-debt, catalog re-score, skill hygiene")
    print("Port as Grok skills when implementing; do not require Hermes/AgenC binary.")


def setup_safety_notes() -> None:
    print("\n=== Safety ===")
    print("  - write-guard-mcp: make smoke-write-guard (default audit)")
    print("  - cage network whitelist: make cage-grok-net-smoke")
    print("  - destructive_command_guard / credential pools: catalog patterns only")


def setup_inference_notes() -> None:
    print("\n=== Local inference ===")
    print("  - Ollama + LiteLLM: make local-ollama-up && make smoke-litellm-ollama")
    print("  - llama.cpp ngram-mod: optional host flag (Entry 051) — not required for cage path")
    if have("llama-cli"):
        print("  llama-cli: available")
    else:
        print("  llama-cli: not on PATH (optional)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--components",
        nargs="*",
        default=DEFAULT_COMPONENTS,
        help="Components to check (default: all)",
    )
    args = parser.parse_args()

    print("pfy-mentat local agent environment check (idempotent)")
    print(f"Repo: {REPO_ROOT}")
    print(f"Components: {args.components}")

    component_map = {
        "operator_path": setup_operator_path,
        "grok_bootstrap": setup_grok_bootstrap,
        "agent_cage": setup_agent_cage,
        "loop_engineering_pack": setup_loop_engineering_pack,
        "eval_harness": setup_eval_harness,
        "memory_notes": setup_memory_notes,
        "hermes_patterns": setup_hermes_patterns,
        "safety_notes": setup_safety_notes,
        "inference_notes": setup_inference_notes,
        # legacy alias: no longer installs AgenC
        "agenc_wrapper": setup_operator_path,
    }

    for comp in args.components:
        fn = component_map.get(comp)
        if fn:
            fn()
        else:
            print(f"[WARN] unknown component: {comp}")

    print("\n=== Done ===")
    print("Authoritative commands: make help | make help-platform | make cage-grok | make eval-v02")
    if AGENTS_MD.is_file():
        print(f"Agent router: {AGENTS_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
