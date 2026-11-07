# mattpocock skills subset (paths snapshot)

- **Upstream:** https://github.com/mattpocock/skills
- **Pin:** `4ae2317ddb22b046e26455e4f9c9b3aaaf62212d` (refreshed 2026-11-07; previous pin `391a2701dd94`)
- **License:** MIT. Copyright (c) 2026 Matt Pocock. The license text is `LICENSE` in this directory. Upstream text is copied verbatim. This file is the local note; do not edit the vendored skill files.
- **Path moves at this pin:** none. `tdd`, `code-review`, and `to-spec` are still `skills/engineering/<name>/`. Upstream added `agents/openai.yaml` beside each of those skills. This snapshot does not copy `agents/`.

## Attribution

| Skill | Upstream path | License |
| --- | --- | --- |
| tdd | https://github.com/mattpocock/skills/tree/4ae2317ddb22b046e26455e4f9c9b3aaaf62212d/skills/engineering/tdd | MIT |
| code-review | https://github.com/mattpocock/skills/tree/4ae2317ddb22b046e26455e4f9c9b3aaaf62212d/skills/engineering/code-review | MIT |
| to-spec | https://github.com/mattpocock/skills/tree/4ae2317ddb22b046e26455e4f9c9b3aaaf62212d/skills/engineering/to-spec | MIT |
| implement | https://github.com/mattpocock/skills/tree/4ae2317ddb22b046e26455e4f9c9b3aaaf62212d/skills/engineering/implement | MIT |
| retro | https://github.com/mattpocock/skills/tree/4ae2317ddb22b046e26455e4f9c9b3aaaf62212d/skills/engineering/retro | MIT |
| grilling | https://github.com/mattpocock/skills/tree/4ae2317ddb22b046e26455e4f9c9b3aaaf62212d/skills/productivity/grilling | MIT |
| grill-me | https://github.com/mattpocock/skills/tree/4ae2317ddb22b046e26455e4f9c9b3aaaf62212d/skills/productivity/grill-me | MIT |
| software-factory | https://github.com/mattpocock/skills/tree/4ae2317ddb22b046e26455e4f9c9b3aaaf62212d/skills/in-progress/software-factory | MIT |

`software-factory` in this snapshot is only `SKILL.md`, `EXAMPLE-TASKS.md`, and `RUNNERS.md`. The other surveys (`GIT-HOSTS.md`, `OBSERVABILITY-PLATFORMS.md`, `TICKET-TRACKERS.md`) are not vendored.

## Curated skills

tdd, code-review, to-spec, implement, retro, grilling, grill-me, software-factory.

## Install

Grok `[skills].paths` points at this directory on Mark's checkout. That path is not copied into `~/.grok/skills`. Do not edit `~/.grok/config.toml` and do not run `install.sh` just to refresh this pin.

Worktree Builds load these skills from `.grok/skills/<name>`. `grilling`, `tdd`, `code-review`, and `to-spec` are relative symlinks into this directory. `implement`, `retro`, `grill-me`, and `software-factory` are thin pointers: upstream sets `disable-model-invocation`, and a symlink of that file stays out of the Grok Build skill list. Each pointer tells the model to follow the vendored file. `to-spec` stays a symlink, so the same flag hides it from that list. `pipeline-retro` is first-party under `.grok/skills/pipeline-retro/` and is not part of this snapshot.

## Refresh

```bash
git clone https://github.com/mattpocock/skills.git "$TMPDIR/mattpocock-skills"
git -C "$TMPDIR/mattpocock-skills" checkout 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d
SRC="$TMPDIR/mattpocock-skills"
DEST=bootstrap/grok-cli/skills-external/mattpocock
cp "$SRC/LICENSE" "$DEST/LICENSE"
copy_skill() {
  local src="$1" name="$2"
  rm -rf "$DEST/$name"
  mkdir -p "$DEST/$name"
  find "$src" -maxdepth 1 -type f -exec cp -a {} "$DEST/$name/" \;
}
copy_skill "$SRC/skills/engineering/tdd" tdd
copy_skill "$SRC/skills/engineering/code-review" code-review
copy_skill "$SRC/skills/engineering/to-spec" to-spec
copy_skill "$SRC/skills/engineering/implement" implement
copy_skill "$SRC/skills/engineering/retro" retro
copy_skill "$SRC/skills/productivity/grilling" grilling
copy_skill "$SRC/skills/productivity/grill-me" grill-me
rm -rf "$DEST/software-factory"
mkdir -p "$DEST/software-factory"
cp -a "$SRC/skills/in-progress/software-factory/SKILL.md" \
      "$SRC/skills/in-progress/software-factory/EXAMPLE-TASKS.md" \
      "$SRC/skills/in-progress/software-factory/RUNNERS.md" \
      "$DEST/software-factory/"
```

`find -maxdepth 1 -type f` keeps `agents/openai.yaml` out. Do not rsync the skill directory with `--delete` from upstream or that file comes back.

## Policy

ADR-0009 hybrid; T-0011. Local pipeline use of `retro` and `software-factory` lives in `.grok/skills/pipeline-retro/SKILL.md`, not in the vendored files.
