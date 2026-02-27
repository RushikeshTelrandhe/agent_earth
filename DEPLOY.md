# Agent Earth — Deployment Guide

Production deployment uses a **split architecture**:
- **Backend** (Python/Flask) → [Railway](https://railway.app)
- **Frontend** (React/Vite) → [Vercel](https://vercel.app)

---

## 1. Backend Deployment (Railway)

### Prerequisites
- [Railway CLI](https://docs.railway.app/develop/cli) installed, or use the web dashboard
- GitHub repo connected

### Steps

```bash
# Login to Railway
railway login

# Create a new project
railway init

# Link to this repo (root directory)
railway link

# Set environment variables
railway variables set ALLOWED_ORIGINS="https://your-frontend.vercel.app"
railway variables set FLASK_ENV="production"

# Deploy
railway up
```

### What happens
- Railway reads `Procfile` → runs `gunicorn wsgi:app`
- Reads `runtime.txt` → uses Python 3.10
- Auto-installs from `requirements.txt`
- Health check at `/health`

### Verify
```
curl https://your-backend.railway.app/health
# → {"status": "ok", "service": "agent-earth-api"}
```

---

## 2. Frontend Deployment (Vercel)

### Prerequisites
- [Vercel CLI](https://vercel.com/docs/cli) installed, or use the web dashboard

### Steps

```bash
# Navigate to frontend
cd dashboard/frontend

# Login
vercel login

# Deploy (first time - set up project)
vercel

# When prompted:
# - Root directory: ./  (dashboard/frontend)
# - Framework: Vite
# - Build command: npm run build
# - Output dir: dist
```

### Environment Variables

Set in Vercel Dashboard → Settings → Environment Variables:

| Variable | Value |
|----------|-------|
| `VITE_API_URL` | `https://your-backend.railway.app/api` |

> **Important**: The `VITE_API_URL` must include the `/api` path prefix.

### Verify
Open your Vercel URL → should load the landing page with the animated earth.

---

## 3. Post-Deploy Checklist

- [ ] `/health` returns `200 OK` on backend
- [ ] Landing page loads on frontend
- [ ] "Launch Simulation" runs successfully
- [ ] 3D Holographic Earth renders without WebGL crashes
- [ ] Crowdsense tab loads independently
- [ ] AI Advisor responds to questions
- [ ] No console errors in production

---

## 4. Environment Variables Reference

### Backend (Railway)
| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `5000` | Auto-set by Railway |
| `ALLOWED_ORIGINS` | `*` | Comma-separated CORS origins |
| `FLASK_ENV` | `production` | Set to `production` in prod |

### Frontend (Vercel)
| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `/api` | Backend API URL (with `/api`) |

---

## 5. Local Development

No changes needed for local dev:

```bash
# Terminal 1 - Backend
python main.py dashboard

# Terminal 2 - Frontend (Vite proxies /api → localhost:5000)
cd dashboard/frontend
npm run dev
```

---

## Architecture Diagram

```
┌─────────────────┐     HTTPS      ┌──────────────────┐
│   Vercel CDN    │ ◄────────────► │    Browser       │
│   (React SPA)   │                │                  │
└────────┬────────┘                └──────────────────┘
         │ VITE_API_URL
         ▼
┌─────────────────┐
│   Railway       │
│   (Flask API)   │
│   gunicorn      │
│   /health       │
│   /api/*        │
└─────────────────┘
```
