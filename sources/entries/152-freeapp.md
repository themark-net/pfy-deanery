### Entry 152: freeapp-class voice coding (freeapp.ai, Stage-0 receipt, reference only)

- **URL**: https://www.freeapp.ai/
- **Date**: 2026-10-30 PT (T-0095). The public page was read. Nothing installed. No source repository was found on that page.
- **Poster / source**: ADR-0012 (2026-07-26) names a class, "freeapp-class Tailscale voice coding", and path F1 "freeapp-class product". It does not cite a URL. The public product at freeapp.ai, fetched 2026-10-30 PT, matches that class: phone voice, a server you own, Tailscale or direct TLS, someone else's coding agent. This receipt does not claim the July ADR linked this site.
- **Summary / Key Claims** (marketing page; not run): An Android client plus a local daemon. "One script" on a Linux box, then pair the phone over TLS or Tailscale. "Say what to build." The agent is "powered by Claude on your own key" (you pay Anthropic). Speech-to-text and text-to-speech are described as on-device. Price on the page: $299 one-time founder license, then $89/mo after founder spots. No installer script, license file, or command was published on the page that was fetched.
- **Extracted Repos / Tools**: None. No git pin.
- **TOOLS.md Link**: None. Stage-0 FAIL / I0 awareness. No TOOLS.md row. No `data/tools.json` row. No stage-card promotion. No triple-write.
- **Notes (Stage-0 gate):**
  - **License:** FAIL. The page sells a founder license ($299, then $89/mo). No open-source LICENSE is shown. That is not a license that allows commercial and research use without a paid grant.
  - **Self-host / quickstart:** FAIL. "One script" and "one command" are claims. The script text, the command, and a timing are not shown. This run did not install it.
  - **Hello-world:** FAIL. "Say what to build" is a product sentence, not a runnable command.
  - **Fail closed:** Stage-0 FAIL / I0 awareness. All three legs fail. No catalog row, no clone, no Make target, no env required var.
  - **Non-goals:** Do not buy or install freeapp. Do not put an Anthropic key in this lab for it. Do not make it the voice runtime. Half-duplex local STT stays the product path (ADR-0012). No Feature GO. Catalog HOLD 70-75 unchanged.
- **Score note (not scored):** I0. No S1-S4 and no tier.
- **How this fails / how we recover:**

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Class treated as a pin | A later edit invents a git SHA or a pass from the marketing sentences | Re-read https://www.freeapp.ai/ and any LICENSE the vendor actually publishes. `tests/test_voice_stage0_ref.py` fails if this receipt says pass while it still has no git pin. |
| Paid license read as open | The $299 line is dropped and the entry is cataloged as permissive | Keep the price sentence until an upstream LICENSE file is quoted. |
| Silent promotion | A TOOLS.md row or a `data/tools.json` object named freeapp | The same test fails. Revert the row. Entry 152 stays the artifact. |

- **Status**: Stage-0 FAIL / I0 awareness (T-0095, issue #10). Receipt only. Not a primary install.
