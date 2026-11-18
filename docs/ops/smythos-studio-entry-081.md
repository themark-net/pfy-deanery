# Ops notes - Entry 081 SmythOS Studio

## Stage 0
- Self-host <5 min: yes (`docker compose up -d` after clone + `.env` copy; UI at http://localhost:6060)
- License: MIT (both Studio and SRE)
- Hello-world: Docker path exercises the visual workspace + runtime

## Suggested TOOLS.md row (Agent Frameworks & Orchestration)

| Tool | Category | Stage scores | Tier | Notes / Tracking |
|------|----------|--------------|------|------------------|
| SmythOS Studio (+ SRE) | Visual Workflow Builders | S1=82 S2=72 S3=85 S4=80 → ~80 | B | Drag-and-drop agent builder + MIT runtime/SDK. Docker self-host. SaaS company exists but OSS core is local. Entry 081. |

## data/tools.json sketch
```json
{
  "name": "SmythOS Studio",
  "repo": "https://github.com/SmythOS/smythos-studio",
  "related": ["https://github.com/SmythOS/sre"],
  "license": "MIT",
  "category": "Agent Frameworks & Orchestration",
  "subcategory": "Visual Workflow Builders",
  "scores": {"S1": 82, "S2": 72, "S3": 85, "S4": 80, "overall": 80},
  "tier": "B",
  "x_post_entry": "081",
  "install": "docker compose up -d (Studio); npm i -g @smythos/cli (SRE)",
  "notes": "Visual drag-and-drop agent builder with deployable local/cloud/edge runtime. MIT OSS core; commercial SaaS available."
}
```

## Merge steps
1. Keep `sources/entries/081-smythos-studio.md` as the entry (or append into x-posts.md if preferred).
2. Add TOOLS.md row + tools.json object on merge or follow-up.
3. No TODO deeper-eval item unless Docker smoke or local-LLM connector issues surface.
