# Deployment Setup

This project deploys the Vite frontend to Vercel and the FastAPI backend to Render.

No real environment values are committed to the repository. Local development works without changing environment variables: the frontend uses the Vite `/api` proxy, and the backend defaults to allowing `http://localhost:5173`.

## Files added

- `.github/workflows/frontend-vercel.yml`: builds and deploys the frontend to Vercel.
- `.github/workflows/backend-render.yml`: tests the backend and triggers a Render deploy.
- `.github/workflows/backend-keepalive.yml`: pings the backend health endpoint every 10 minutes.
- `GET /healthz`: lightweight backend health endpoint for keep-alive checks.
- `frontend/src/api.ts`: chooses the local proxy automatically in development and the Render URL in GitHub Actions builds.

## One-place deployment configuration

Use GitHub **Actions variables** for non-secret deployment URLs. These are the values you change when moving to another Vercel or Render URL.

Go to **GitHub repository > Settings > Secrets and variables > Actions > Variables** and add:

| Variable | Example | Used by |
| --- | --- | --- |
| `BACKEND_BASE_URL` | `https://<your-render-service>.onrender.com` | Frontend production build and keep-alive workflow |

Use GitHub **Actions secrets** only for credentials and private deploy hooks.

Go to **GitHub repository > Settings > Secrets and variables > Actions > Secrets** and add:

| Secret | Used by |
| --- | --- |
| `VERCEL_TOKEN` | Vercel CLI authentication |
| `VERCEL_ORG_ID` | Vercel project lookup |
| `VERCEL_PROJECT_ID` | Vercel project lookup |
| `RENDER_DEPLOY_HOOK_URL` | Backend deploy trigger |

## Render backend setup

1. In Render, create a new **Web Service** from this GitHub repository.
2. Use these service settings:
   - Runtime: `Python`
   - Branch: `main`
   - Root directory: leave empty
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
3. In Render, add this backend runtime environment variable:
   - `CORS_ORIGINS=["https://<your-vercel-app>.vercel.app"]`
4. Deploy the service once.
5. Open `https://<your-render-service>.onrender.com/healthz`.
6. Confirm it returns `{"status":"ok"}`.
7. In the Render service dashboard, open **Settings** and copy the **Deploy Hook** URL.
8. Add that URL to GitHub as the secret `RENDER_DEPLOY_HOOK_URL`.
9. Add `https://<your-render-service>.onrender.com` to GitHub as the variable `BACKEND_BASE_URL`.

If you later add a custom Vercel domain, update Render's `CORS_ORIGINS` value:

```text
["https://<your-vercel-app>.vercel.app","https://<your-custom-domain>"]
```

## Vercel frontend setup

1. In Vercel, create a new project from this GitHub repository.
2. Use these project settings:
   - Framework preset: `Vite`
   - Root directory: `frontend`
   - Install command: `npm ci`
   - Build command: `npm run build`
   - Output directory: `dist`
3. Do not add `VITE_API_BASE_URL` in Vercel for this GitHub Actions pipeline. The GitHub workflow injects it from the single GitHub variable `BACKEND_BASE_URL`.
4. Deploy once from Vercel so the project exists and you have a production URL.
5. Update Render's `CORS_ORIGINS` with that Vercel production URL.
6. If you only want GitHub Actions to deploy, disable Vercel's automatic Git deployments after confirming the GitHub Action works.

To get the Vercel IDs for GitHub secrets:

```powershell
cd frontend
npx vercel login
npx vercel link
Get-Content .vercel\project.json
```

Use:

- `orgId` as `VERCEL_ORG_ID`
- `projectId` as `VERCEL_PROJECT_ID`

Create a Vercel access token in Vercel account settings and save it as `VERCEL_TOKEN`.

## Local development behavior

You do not need to change deployment variables for local development.

Frontend local behavior:

- Command: `cd frontend && npm run dev`
- Browser requests go to `/api/...`.
- `vite.config.ts` proxies `/api/...` to `http://127.0.0.1:8000` and strips the `/api` prefix.
- `VITE_API_BASE_URL` is intentionally unset locally.

Backend local behavior:

- Command: `uvicorn backend.main:app --reload`
- Default CORS origin is `http://localhost:5173`.
- Local health endpoint is `http://127.0.0.1:8000/healthz`.

Production behavior:

- GitHub Actions sets `VITE_API_BASE_URL` from `BACKEND_BASE_URL` during the Vercel build.
- The browser calls Render directly, for example `https://<your-render-service>.onrender.com/upload`.
- The keep-alive workflow calls `https://<your-render-service>.onrender.com/healthz`.

## How the workflows behave

- A push to `main` that changes `frontend/**` deploys the frontend to Vercel.
- A push to `main` that changes `backend/**`, `requirements.txt`, or `pytest.ini` runs backend tests and triggers a Render deploy.
- The keep-alive workflow runs every 10 minutes and calls `${BACKEND_BASE_URL}/healthz`.
- All workflows can also be started manually from the GitHub Actions tab with **Run workflow**.

## Keep-alive note

Render Free web services spin down after 15 minutes without inbound traffic. The scheduled GitHub Action pings `/healthz` every 10 minutes to reduce cold starts. GitHub scheduled workflows can be delayed, so this is a practical workaround, not a hard uptime guarantee. A paid Render instance is the reliable option for production uptime.

## Reference docs

- Vercel GitHub Actions deployment: https://vercel.com/kb/guide/how-can-i-use-github-actions-with-vercel
- Render deploy hooks: https://render.com/docs/deploy-hooks
- Render free service sleep behavior: https://render.com/docs/free
- GitHub scheduled workflows: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
