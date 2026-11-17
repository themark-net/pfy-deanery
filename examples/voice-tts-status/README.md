# Optional short local TTS status (T-0094)

Half-duplex **status only** (ADR-0012): a short spoken "done" or "fail" after a voice agent run. This is not duplex voice, not TTS of the full reply, and not a required install.

## Opt in

Default is **off**. Nothing is spoken, no TTS binary is started, and no voice model is downloaded.

```bash
# After a voice agent run, or by itself:
VOICE_TTS=1 python3 examples/voice-tts-status/speak_status.py done
VOICE_TTS=1 python3 examples/voice-tts-status/speak_status.py fail

# Same opt-in on the voice agent runner (examples/voice-stt-edge):
VOICE_TTS=1 VOICE_AUTO_AGENT=mock make voice-agent-run
```

`VOICE_TTS` must be `1`, `true`, `yes`, or `on`. Any other value, including unset, is silence.

## Which binary

The helper uses the first host binary already on `PATH`:

| Binary | When it runs |
|--------|----------------|
| `espeak-ng` or `espeak` | Preferred. No extra model file. |
| `say` | macOS. |
| `piper` | Only when `VOICE_TTS_PIPER_MODEL` is an **existing** local model file. The path is never fetched. |

If no usable binary is found, the helper skips, logs why, and exits 0. A TTS error also skips (exit 0) and does not fail the agent run.

Install a backend yourself if you want audio, for example `espeak-ng` from the distro. Kokoro and a piper voice-model install are later, optional, and not started from this helper.

`make smoke-voice-tts` is still a probe (is a binary present?). It does not speak and it does not install anything.
