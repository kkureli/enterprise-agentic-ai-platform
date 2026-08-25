# Demo media workflow

Generate curated README screenshots, a short animated preview, and a full
product demo recording from the **live** Enterprise Agentic AI Playground.

## Command

```bash
./scripts/demo/generate-media.sh            # screenshots + GIF + MP4
./scripts/demo/generate-media.sh --screenshots
./scripts/demo/generate-media.sh --preview
./scripts/demo/generate-media.sh --video
LIVE_DEMO_URL=https://… ./scripts/demo/generate-media.sh --all
```

Equivalent:

```bash
cd scripts/demo && npm install && npm run demo:media -- --all
```

**Not run from CI.** Live AI usage is bounded (`MAX_AI_REQUESTS` in
`scripts/demo/src/config.ts`). HITL demos **Reject** write actions.

## Outputs

| Path | Tracked? | Purpose |
|------|----------|---------|
| `docs/assets/hero-playground.png` | yes | README hero |
| `docs/assets/tenant-isolation.png` | yes | E-100 Atlas vs Borealis |
| `docs/assets/execution-trace.png` | yes | Trace panel |
| `docs/assets/compare-runs.png` | yes | Standard vs Advanced |
| `docs/assets/evaluation.png` | yes | Regression metrics |
| `docs/assets/rag-architecture.png` | yes | RAG Pipeline Explorer |
| `docs/assets/demo-preview.gif` | yes | Short README animation |
| `artifacts/demo/enterprise-agentic-ai-demo.mp4` | **no** | Full ~60–90s demo |
| `artifacts/demo/enterprise-agentic-ai-demo.webm` | **no** | Raw Playwright capture |
| `artifacts/demo/demo-preview.webp` | **no** | Optional smaller preview |

## Full video URL

Published GitHub Release asset:

https://github.com/kkureli/enterprise-agentic-ai-platform/releases/download/demo-v1/enterprise-agentic-ai-demo.mp4

Local regenerations still write `artifacts/demo/enterprise-agentic-ai-demo.mp4`
(gitignored). Re-upload to a new release tag if the public URL should change.

## Requirements

- Node.js 20+
- Playwright Chromium (`npx playwright install chromium`)
- `ffmpeg` (GIF/MP4)
- ImageMagick `magick` (PNG optimize + tenant-isolation collage)

Default playground URL:

`https://white-river-0fe20910f.7.azurestaticapps.net`

## README visual blocks

Tracked under `docs/assets/` and linked from `README.md`:

1. Hero playground
2. Animated preview GIF
3. Tenant-isolation collage
4. Compare Runs
5. RAG Pipeline Explorer

`evaluation.png` and `execution-trace.png` are generated for portfolio use; keep
the main README to about five large visuals.
