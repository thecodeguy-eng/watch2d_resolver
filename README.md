# Watch2D Resolver

A tiny standalone service that turns a raw download "landing" URL into the real
(token-gated) direct download link — the same logic as the website's
`/resolve-download/` view, but running **independently of the main site** so
downloads stay fast even when watch2d.org is slow or down.

```
GET /resolve-download/?url=<landing_url>
->  { "download_url": "<direct or fallback url>" }
```

It reuses your exact scraping logic (cloudscraper for Cloudflare, the
downloadwella POST form, the loadedfiles session warm-up, HTML regex extract).

---

## Run locally

```bash
cd watch2d_resolver
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
# test:
# http://localhost:8000/resolve-download/?url=<some downloadwella url>
```

## Deploy (pick one)

The links are token-gated and expire, so this service must be **reachable every
time someone downloads**. Use a plan that stays warm (no cold-start sleep).

### Render (Docker) — easiest
1. Push this `watch2d_resolver/` folder to a GitHub repo.
2. Render → New → Web Service → connect the repo.
3. It auto-detects the `Dockerfile`. Choose the **Starter** plan (stays warm;
   the Free plan sleeps after 15 min → slow first download).
4. Deploy. Your URL will be `https://watch2d-resolver.onrender.com`.

### Fly.io — cheap, low cold-start
```bash
fly launch --dockerfile Dockerfile   # creates fly.toml, pick a name/region
fly deploy
# keep one machine always on:
fly scale count 1 --region <your-region>
```

### Railway — usage-based
New Project → Deploy from repo → it builds the Dockerfile automatically.

---

## Point the app at it

In the Flutter app, open `lib/config/constants.dart` and set:

```dart
static const String resolverBase = 'https://watch2d-resolver.onrender.com';
```

Leave it empty (`''`) to keep using the main site. Once set, the app resolves
downloads through this service instead — independent of watch2d.org.

## Keeping it warm (free tiers)
If you must use a free/sleeping tier, ping it every ~10 min so it never sleeps:
a free cron (e.g. cron-job.org / UptimeRobot) hitting `GET /` works fine.
