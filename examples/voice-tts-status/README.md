# Optional short local TTS status (T-0094)

Half-duplex **status only** (ADR-0012): a short spoken "done" or "fail" after a voice agent run. This is not duplex voice, not TTS of the full reply, and not a required install.

## Opt in

Default is **off**. Nothing is spoken, no TTS binary is started, and no voice model is downloaded.

```bash
# After a voice agent run, or by itself (short status, the default):
VOICE_TTS=1 python3 examples/voice-tts-status/speak_status.py done
VOICE_TTS=1 python3 examples/voice-tts-status/speak_status.py fail

# Opt in to a clipped reading of the agent reply (not phone playback):
VOICE_TTS=1 VOICE_TTS_MODE=reply python3 examples/voice-tts-status/speak_status.py --mode reply "The tests passed."

# Same opt-in on the voice agent runner (examples/voice-stt-edge):
VOICE_TTS=1 VOICE_AUTO_AGENT=mock make voice-agent-run
VOICE_TTS=1 VOICE_TTS_MODE=reply VOICE_AUTO_AGENT=mock make voice-agent-run
```

`VOICE_TTS` must be `1`, `true`, `yes`, or `on`. Any other value, including unset, is silence.

`VOICE_TTS_MODE` defaults to `status` (a short “done” or “fail”). Set it to `reply` or `full` to speak the agent reply, clipped to 400 characters on a word boundary. A typo in the mode does not switch to the full reply. Phone playback is out of scope.

## Which binary

The helper uses the first host binary already on `PATH`:

| Binary | When it runs |
|--------|----------------|
| `espeak-ng` or `espeak` | Preferred. No extra model file. |
| `say` | macOS. |
| `piper` | Only when `VOICE_TTS_PIPER_MODEL` is an **existing** local model file. The path is never fetched. |

If no usable binary is found, the helper skips, logs why, and exits 0. A TTS error also skips (exit 0) and does not fail the agent run.

Install a backend yourself if you want audio, for example `espeak-ng` from the distro. A piper voice-model install is still optional and manual (`VOICE_TTS_PIPER_MODEL` must point at an existing local file; nothing is fetched). Kokoro was catalog-fit checked on 2026-11-17 and came back a confident **redundant** versus the existing piper/espeak path; it is not wired and its weights are not downloaded. See [kokoro-fit.md](kokoro-fit.md).

`make smoke-voice-tts` is still a probe (is a binary present?). It does not speak and it does not install anything.
