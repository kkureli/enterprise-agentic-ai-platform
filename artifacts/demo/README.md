# Demo recordings (not committed)

Large video files stay outside normal Git history.

Regenerate:

```bash
./scripts/demo/generate-media.sh --all
# or
./scripts/demo/generate-media.sh --video
```

Outputs:

- `enterprise-agentic-ai-demo.webm` / `.mp4` — full product demo
- `demo-preview.webp` — optional compact animated preview (GIF for README is under `docs/assets/`)

## Publishing the full MP4

Public URL (GitHub Release `demo-v1`):

https://github.com/kkureli/enterprise-agentic-ai-platform/releases/download/demo-v1/enterprise-agentic-ai-demo.mp4

Re-upload to a new release if you regenerate and want that URL updated in
`README.md` / `docs/demo-media.md`.
