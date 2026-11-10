# G.I KO KO Automation — initial setup

## Current state

The initial Automation API foundation is installed alongside the existing G.I KO KO AI API.
It reports whether platform credentials are present. It does **not** publish posts yet.
Publishing remains disabled until official platform OAuth/API validation and durable
scheduled-job storage are implemented.

## Supported platform credential names

Set these only in Render > gi-koko-ai-api > Environment:

- Facebook Page: META_PAGE_ACCESS_TOKEN, META_PAGE_ID
- Instagram: META_IG_ACCESS_TOKEN, META_IG_USER_ID
- YouTube: YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN
- TikTok: TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_ACCESS_TOKEN
- Admin endpoint: AUTOMATION_ADMIN_SECRET

Do not commit credentials, put them in source files, or paste them into chat.
The API status endpoint reveals missing variable names only, never credential values.

## API

- GET /api/automation/status
- POST /api/automation/admin/check with header X-Automation-Secret

## Important

A Render Free web service may sleep and its local filesystem is not durable storage.
Do not store OAuth refresh tokens or scheduled post queues in SQLite on the free
ephemeral filesystem. Configure a persistent database before enabling auto-publishing.

Each platform requires its own developer app, approved scopes, account eligibility,
and user authorization. TikTok Content Posting API access can require app review;
YouTube API use is quota-limited; Meta Page and Instagram publishing require the
correct Page/Instagram account permissions.
