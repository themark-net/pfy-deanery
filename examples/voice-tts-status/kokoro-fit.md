# Kokoro catalog-fit receipt (T-0094, 2026-11-17)

**Flow:** existing `scripts/catalog_fit_triage.py` `triage("kokoro", subject=..., write=False)` on local `qwen3.6:35b`. No model pull, no cloud call, no `--write` into `eval/catalog-fit/` (Kokoro has no stage card or TOOLS.md row).

**Subject (honest, not a catalog row):** hexgrad/Kokoro-82M, Apache-2.0 local neural TTS, optional quality upgrade over the host espeak/piper path already wired in this example. Non-goals: duplex, phone playback, required install, auto-download.

**Result**

| Field | Value |
|-------|--------|
| model | `qwen3.6:35b` |
| exit | 0 |
| chip_conf | conf ok |
| confidence | 0.95 (gate 0.85) |
| verdict | `redundant` |
| fit | false |
| overlap_with | `piper` |

**Reason (model):** Kokoro is an optional local TTS model. The catalog already includes Piper (and espeak-ng) for local TTS needs. Kokoro duplicates the function of providing local neural TTS without filling a unique gap that Piper cannot address, especially given its optional tag and the explicit note that it is not a required install.

**Note:** `piper` is not a TOOLS.md / `data/stages` slug. It is the already-wired optional host path in this example (`piper` when `VOICE_TTS_PIPER_MODEL` is an existing local file, else espeak-ng / espeak / say). The confident negative verdict still holds: no unique gap versus that safe default.

**Decision:** Do **not** wire a Kokoro path, do **not** download weights, and do **not** add a catalog row from this check. A later pull, if the design is revised, would still have to be explicit opt-in through the 25 GB pull gate.
