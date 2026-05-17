# Coolify Deployment Guide

This guide walks through deploying the Notes for Emi application on Coolify. It assumes you already have Coolify installed and running on your Oracle Cloud VM.

---

## 1. Connect the GitHub Repository

1. In the Coolify dashboard, go to **Sources** → **Add New Source**.
2. Select **GitHub** and authenticate with your GitHub account.
3. Grant Coolify access to the repository containing the project (e.g. `your-username/EmiSofiaWebsite`).

Once connected, Coolify can pull source code and build Docker images directly from the repo.

---

## 2. Create the Backend Service

### Step 2a: Add a new resource

1. Go to **Projects** in the left sidebar.
2. Click on your project (or click **+ Add** to create one — name it something like "Emi Sofia").
3. Inside the project, click **+ Add New Resource**.
4. You'll see a list of resource types. Select **Public Repository** (if your repo is public) or **Private Repository (with GitHub App)** if it's private.
5. If prompted, select the GitHub source you connected in step 1.
6. Pick the repository (e.g. `EmiSofiaWebsite`) and the branch (`main`).

### Step 2b: Configure the build

After selecting the repo, Coolify will ask how to build it:

1. For **Build Pack**, select **Dockerfile**.
2. Set these fields:
   - **Base Directory**: `/backend` — this tells Coolify the Dockerfile and source code live in the `backend/` subdirectory of the repo.
   - **Dockerfile Location**: `/backend/Dockerfile` — path to the Dockerfile relative to the repo root.
   - **Port Exposes**: `8000` — the port your FastAPI app listens on inside the container.
3. Give the resource a name like `emisofia-backend` so it's easy to identify.

### Step 2c: Add a persistent volume for the database

The Storages option is only available **after** the resource has been created. You won't see it during the initial setup wizard.

1. First, complete the initial resource creation (steps 2a and 2b) and do an initial deploy.
2. Once the resource exists, go to its detail page.
3. Look for the **Storages** tab in the resource's settings (left sidebar or top navigation tabs).
4. Click **+ Add** to create a new volume mount.
5. Fill in:
   - **Name**: `emisofia-db` (or any descriptive name)
   - **Destination Path**: `/data` — this is the path inside the container where the volume is mounted. The app creates `emisofia.db` inside this directory.
   - **Source Path**: Leave blank to let Coolify manage it automatically (it creates a directory under `/data/coolify/volumes/`). Or specify a custom host path if you prefer.
6. Save and **redeploy** the resource — Coolify will recreate the container with the volume mounted.

> **Why `/data` and not `/data/emisofia.db`?** Docker volumes mount at directory level, not file level. The app writes to `/data/emisofia.db` inside the container, and the volume ensures the entire `/data` directory persists.

### Step 2d: Set environment variables

Go to the resource's **Environment Variables** tab and add each variable (see Section 5 below for the full list). The critical ones for the backend to start:

- `CMS_PASSWORD_HASH` — without this, login won't work
- `JWT_SECRET` — without this, token signing/verification fails
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `S3_BUCKET`, `CLOUDFRONT_DOMAIN` — needed for photo uploads

### Step 2e: Deploy

1. Click **Deploy** (or it may auto-deploy if you enabled webhooks).
2. Watch the build logs — Coolify will pull the repo, build the Docker image from `backend/Dockerfile`, and start the container.
3. Once running, the backend is accessible internally on port 8000. Coolify's Traefik proxy will route external traffic to it based on the domain rules you set up in Section 4.

---

## 3. Create the Frontend Service

1. In the same project, click **Add New Resource** again.
2. Choose **Docker** → **Dockerfile** as the build method.
3. Select the same GitHub repository and branch.
4. Configure the build:
   - **Build context**: `./frontend`
   - **Dockerfile path**: `./frontend/Dockerfile`
5. Set the **exposed port** to `3000`.
6. No persistent volume is needed for the frontend — it's stateless.

---

## 4. Configure Domain Routing

Both services share the domain `emisofia.com`. Coolify's built-in Traefik proxy handles path-based routing.

### Backend service domain settings

1. Open the backend service settings → **Domains**.
2. Set the domain to: `https://emisofia.com/api`
3. This tells Coolify/Traefik to route all requests matching `/api/*` to the backend container on port 8000.

### Frontend service domain settings

1. Open the frontend service settings → **Domains**.
2. Set the domain to: `https://emisofia.com`
3. This routes all other requests (`/*`) to the frontend container on port 3000.

> **Routing priority**: Coolify/Traefik uses longest-prefix matching, so `/api/*` takes priority over `/*` for API requests. If Coolify requires explicit path rules, configure:
> - Backend: path prefix `/api`
> - Frontend: path prefix `/` (catch-all)

---

## 5. Set Environment Variables

In Coolify, go to each service's **Environment Variables** section and add the following.

### Backend service environment variables

| Variable | Description | Example |
|---|---|---|
| `CMS_PASSWORD_HASH` | bcrypt hash of the CMS login password. Generate with: `python -c "import bcrypt; print(bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode())"` | `$2b$12$...` |
| `JWT_SECRET` | A long random string used to sign JWT tokens (HS256). Generate with: `openssl rand -hex 32` | `a1b2c3d4e5...` |
| `AWS_ACCESS_KEY_ID` | IAM access key with `s3:PutObject` and `s3:DeleteObject` permissions on the photos bucket | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | IAM secret key paired with the access key above | `wJalr...` |
| `AWS_REGION` | AWS region where the S3 bucket lives | `us-east-1` |
| `S3_BUCKET` | Name of the S3 bucket for photo storage | `emisofia-photos` |
| `CLOUDFRONT_DOMAIN` | CloudFront distribution domain (without `https://`) | `d1234abcd.cloudfront.net` |
| `CORS_ORIGINS` | Comma-separated list of allowed origins for CORS | `https://emisofia.com` |

### Frontend service environment variables

| Variable | Description | Example |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Base URL the browser uses to call the API. Since both services share the same domain, use the public URL. | `https://emisofia.com` |
| `REVALIDATE_SECRET` | Secret token used by the CMS to trigger Next.js on-demand ISR revalidation. Must match what the CMS sends. | `my-revalidation-secret-123` |
| `NEXT_PUBLIC_REVALIDATE_SECRET` | Same value as `REVALIDATE_SECRET` — exposed to the client so the CMS pages can call the revalidation endpoint. | `my-revalidation-secret-123` |

> **Security note**: Never commit real values to the repository. All secrets are managed exclusively through Coolify's UI.

---

## 6. Enable Auto-Redeploy on Push

1. In each service's settings, find the **Webhooks** or **Auto Deploy** section.
2. Enable **Auto Deploy** (sometimes labelled "Webhook" or "Git Push Deploy").
3. Coolify will automatically rebuild and redeploy the service whenever a new commit is pushed to the configured branch.

If Coolify shows a webhook URL, add it to your GitHub repository under **Settings** → **Webhooks** with the `push` event. Alternatively, Coolify's GitHub App integration handles this automatically.

---

## 7. SSL/TLS (Automatic)

Coolify handles SSL/TLS automatically via Let's Encrypt:

- When you set `emisofia.com` as the domain for your services, Coolify provisions an SSL certificate automatically.
- Certificate renewal is handled in the background — no manual Certbot commands or cron jobs needed.
- HTTP → HTTPS redirect is enabled by default for all configured domains.

No action required beyond setting the domain in step 4.

---

## 8. Database Backup Service (Optional)

A daily backup of the SQLite database can be configured as a separate Coolify service.

1. In the same project, click **Add New Resource**.
2. Choose **Docker** → **Dockerfile**.
3. Configure the build:
   - **Build context**: `./scripts`
   - **Dockerfile path**: `./scripts/Dockerfile.backup`
4. Under **Storages**, mount the **same volume** used by the backend service:
   - **Mount path in container**: `/data`
   - This gives the backup container read access to the live database file.
5. Set the following environment variables:

| Variable | Description | Example |
|---|---|---|
| `AWS_ACCESS_KEY_ID` | IAM credentials with `s3:PutObject` on the backups bucket | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | IAM secret key | `wJalr...` |
| `AWS_REGION` | AWS region for the backups bucket | `us-east-1` |

6. The backup container runs a daily cron job that:
   - Creates a SQLite backup: `sqlite3 /data/emisofia.db ".backup /tmp/emisofia-YYYYMMDD.db"`
   - Uploads it to S3: `aws s3 cp /tmp/emisofia-YYYYMMDD.db s3://emisofia-backups/db/`
   - Cleans up the temp file

> **Note**: This service doesn't need a domain or exposed port — it only runs the cron job internally.

---

## Summary Checklist

- [ ] GitHub repository connected in Coolify
- [ ] Backend service created (build context `./backend`, port 8000, volume at `/data`)
- [ ] Frontend service created (build context `./frontend`, port 3000)
- [ ] Domain routing configured (`/api/*` → backend, `/*` → frontend)
- [ ] All backend environment variables set
- [ ] All frontend environment variables set
- [ ] Auto-redeploy enabled on both services
- [ ] SSL certificate provisioned (automatic)
- [ ] (Optional) Backup service created with shared volume
