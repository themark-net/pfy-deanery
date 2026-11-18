# Remote Android → host STT → tool-capable agent (T-0091 p4a)

**Status:** Live · browser optional  
**Depends:** Phase 1 local STT (`make voice-stt-install`) · OQ-0010 path A  
**Not:** Grok mobile voice (no tools) · Hermes primary · open internet agent phone

## Prefer an app client if the browser hangs

There is no special Play Store “voice agent” required. The host exposes a small
HTTP API over Tailscale; **any** client that can POST works.

| Client | When |
|--------|------|
| **Termux + termux-voice-send.sh** | **Recommended** - record + curl, clear errors |
| **HTTP Shortcuts** | GUI POSTs without Terminal |
| Chrome to `http://100.x:8787/` | Optional; hangs usually mean bind/URL wrong |

Full client recipes: [examples/voice-stt-edge/clients/README.md](../../examples/voice-stt-edge/clients/README.md)

## Goal

```text
  Android (Termux or browser)
       │  Tailscale → host:8787
       ▼
  host remote_server.py
       │  faster-whisper
       ▼
  .generated/handoff.sh → grok (tools) / opencode
```

## Host setup

```bash
make voice-stt-install

# If Tailscale is up, remote.sh defaults to 0.0.0.0
make voice-remote

# Force phone-reachable bind:
VOICE_REMOTE_HOST=0.0.0.0 make voice-remote
```

Note host Tailscale IP:

```bash
tailscale ip -4
cat examples/voice-stt-edge/.generated/remote.token
```

**From phone**, connectivity must work first:

```bash
curl -m 5 http://100.x.y.z:8787/ping
# → pong
```

If `/ping` hangs, the browser will hang too - fix Tailscale/bind/firewall, not STT.

## Termux (recommended)

On phone:

```bash
pkg install termux-api curl jq coreutils
# + install Termux:API app
```

`~/.voice-remote.env`:

```bash
export VOICE_REMOTE_URL='http://100.x.y.z:8787'
export VOICE_REMOTE_TOKEN='…from host remote.token…'
```

```bash
bash termux-voice-send.sh
bash termux-voice-send.sh --text 'run make eval-structural'
```

Copy script from repo: `examples/voice-stt-edge/clients/termux-voice-send.sh`

Then on host:

```bash
examples/voice-stt-edge/.generated/handoff.sh
```

## Browser UI (optional)

Only after `/ping` returns `pong`.

### Why Brave shows “getUserMedia undefined” / no mic prompt

Browsers treat **plain `http://100.x.y.z` as insecure**. On insecure pages,
`navigator.mediaDevices` is **undefined** - Brave/Chrome never show a mic
permission dialog. This is expected, not a bug in our server.

| Approach | Mic in browser? |
|----------|-----------------|
| `http://100.x:8787` | **No** in-page mic |
| **File capture** on the page (`accept=audio` + `capture`) | **Yes** (system recorder) |
| **HTTPS via `tailscale serve`** | **Yes** in-page mic |
| **Termux** | **Yes** (best) |
| Typed text on the page | N/A (always works) |

### Enable in-page mic (HTTPS on Tailscale)

**Architecture (important):**

```text
Phone Brave  ──HTTPS :443──►  tailscale serve  ──HTTP :8787──►  Python voice-remote
                 (TLS ends here)                    (plain HTTP only)
```

Python **never** speaks TLS.

Your logs match this pattern:

```text
GET / HTTP/1.1  200          ← first load over plain http://100.x:8787 worked
TLS handshake on plain HTTP  ← Brave then tried https://100.x:8787 → ERR_SSL_PROTOCOL_ERROR
```

Brave’s **“Always use secure connections”** upgrades `http://` → `https://` on the
**same host:port**. Upgrading to `https://…:8787` cannot work.

On the **host** (two terminals):

```bash
# Terminal A - HTTP backend
VOICE_REMOTE_HOST=127.0.0.1 make voice-remote

# Terminal B - HTTPS front door on :443 (helper prints the phone URL)
make voice-remote-serve
# same as: ./examples/voice-stt-edge/tailscale-serve.sh
```

Open **only** the `https://…ts.net/` URL printed (MagicDNS, **port 443, no :8787**).

| URL | Result |
|-----|--------|
| `https://nimo.<tailnet>.ts.net/` | Good (Serve → Python) |
| `http://127.0.0.1:8787/ping` on host | Good (backend) |
| `http://100.x:8787/` | Loads once, then Brave often SSL-errors |
| `https://100.x:8787/` | **ERR_SSL_PROTOCOL_ERROR** |
| `https://nimo…:8787/` | **ERR_SSL_PROTOCOL_ERROR** |

**Brave workaround without Serve:** Settings → Privacy and security →
turn off **Always use secure connections**, then stay on `http://` and use
**file capture / text** (in-page mic still blocked on plain HTTP).

To stop Serve: `tailscale serve reset`

### Without HTTPS (works today)

1. Reload the page after sync - use **“Pick / capture audio file”** (system mic UI).  
2. Or **Send text**.  
3. Or Termux: `termux-voice-send.sh`.

## API

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/ping` | no | plain `pong` - use this to debug hangs |
| GET | `/health` | no | JSON |
| GET | `/` | no | mobile HTML UI |
| POST | `/api/text` | Bearer | JSON `{"text","target"}` |
| POST | `/api/audio` | Bearer | JSON base64 (browser) |
| POST | `/api/audio-raw` | Bearer | raw body (Termux/curl); headers `X-Voice-Target`, `Content-Type` |
| GET | `/api/last` | Bearer | last transcript |

## Security

| Do | Do not |
|----|--------|
| Tailscale only | Port-forward 8787 to the public internet |
| Keep `remote.token` secret | Commit the token |
| Allow 8787 from tailnet if firewalling | Assume browser HTTPS without Tailscale Serve |

## Smoke

```bash
make smoke-voice-remote
```

## Later

Auto-run Grok on upload, TTS back to phone, true VoIP - not this slice.
