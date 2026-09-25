# Module: Gemini adapter

**Purpose:** Exec `gemini` or `gemini-cli` from `./pfy start gemini`. Inference via `LOCAL_OPENAI_BASE_URL` from the ADR-0014 detector when ready (`OPENAI_BASE_URL` defaults to that). Do not invent Gemini-specific flags.

## Entry

```bash
./pfy harness use gemini
./pfy start gemini
```

Detect: `gemini` or `gemini-cli` on PATH.

Missing binary: `STUB harness: gemini`, issue #59, installer from `data/harnesses.json` `setup`, exit 2. `./pfy start gemini` does not run the installer. No fake ready. Credentials/2FA are owner-only. Gemini has no Attach profile.

```bash
npm install -g @google/gemini-cli
gemini   # login in the CLI
```

Upstream: [google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli)

## Not yet

- Vendoring Gemini CLI into git
- Invented Gemini flags
- Other harness adapters
