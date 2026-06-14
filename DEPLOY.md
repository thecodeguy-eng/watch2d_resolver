# Deploy the Watch2D Resolver (Render free tier)

Everything you need is already in this folder. Follow these steps in order.

```
watch2d_resolver/
  app.py            ← the service
  requirements.txt  ← dependencies
  Dockerfile        ← Render uses this automatically
  render.yaml       ← optional blueprint
  Procfile          ← alternative start command
  .gitignore
  README.md
```

---

## Step 1 — Push this folder to GitHub

Open a terminal **inside the `watch2d_resolver` folder** and run:

```bash
git init
git add -A
git commit -m "Watch2D resolver service"
git branch -M main
```

Create a new **empty** repo on GitHub (https://github.com/new) named
`watch2d-resolver` — do NOT add a README/.gitignore (this folder already has them).

Then connect and push (replace YOUR-USERNAME):

```bash
git remote add origin https://github.com/YOUR-USERNAME/watch2d-resolver.git
git push -u origin main
```

---

## Step 2 — Create the service on Render

1. Go to https://dashboard.render.com → **New +** → **Web Service**.
2. **Connect** your GitHub and pick the `watch2d-resolver` repo.
3. Render auto-detects the **Dockerfile** — leave that as is.
4. Settings:
   - **Name:** `watch2d-resolver` (this becomes your URL)
   - **Instance Type:** **Free**
   - **Health Check Path:** `/`
5. Click **Create Web Service** and wait for the build to go green (a few minutes).

Your URL will look like:
```
https://watch2d-resolver.onrender.com
```

### Test it
Open in a browser:
```
https://watch2d-resolver.onrender.com/
```
You should see: `{"status":"ok","service":"watch2d-resolver"}`

---

## Step 3 — Keep it awake (UptimeRobot, free)

The free Render tier sleeps after 15 min idle. A free pinger keeps it warm:

1. Sign up at https://uptimerobot.com (free).
2. **+ Add New Monitor**
   - **Monitor Type:** HTTP(s)
   - **Friendly Name:** Watch2D Resolver
   - **URL:** `https://watch2d-resolver.onrender.com/`
   - **Monitoring Interval:** 5 minutes
3. **Create Monitor.**

That's it — Render now always sees traffic and never sleeps.

---

## Step 4 — Point the app at it

In the Flutter app, open `lib/config/constants.dart` and set:

```dart
static const String resolverBase = 'https://watch2d-resolver.onrender.com';
```

Hot-restart the app. Downloads now resolve through this service — independent
of watch2d.org.

---

## Done
- Browsing / streaming → Supabase (already independent)
- Simple download links → resolved in-app
- Token-gated links → resolved by THIS service (independent + kept warm)
