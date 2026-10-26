# G.I KO KO AI News Automation — Phase 1

This phase creates source-linked Burmese AI-news drafts as GitHub Issues for human review. It does **not** publish anything to Facebook automatically.

## Schedule
GitHub Actions runs at 07:00, 10:00, 13:00, 16:00 and 19:00 Asia/Yangon. Scheduled Actions can be delayed by GitHub, so these are target times rather than a strict SLA.

## Required GitHub configuration
In repository Settings → Secrets and variables → Actions:
- Add **one** secret: `MODELGO_API_KEY` or `GEMINI_API_KEY`.
- Optional variable `MODELGO_BASE_URL`: `https://api.modelgo.ai/v1`.
- Optional variable `NEWS_MODEL`: `openai/gpt-oss-120b` (must be available on your provider account).

The built-in `GITHUB_TOKEN` is supplied by Actions; workflow permissions grant it issue creation. Never commit API keys into files.

## Review process
Open the repository Issues tab and review issues titled `[NEWS REVIEW]`. Open the original source, verify claims, edit the Burmese copy, and complete the checklist. The draft workflow deliberately does not publish posts.

## Safety / limitations
- RSS feeds may be unavailable or change format.
- A source URL is used to reduce duplicates; this is not a perfect deduplication system.
- AI output can be wrong. Always verify claims against the original source.
- Phase 1 is text-only. Image generation, video rendering, an approval dashboard, persistent audit logs, and publishing to the connected Facebook Page are later phases.
- Use only images/video you own, generated yourself, or are licensed to reuse.
