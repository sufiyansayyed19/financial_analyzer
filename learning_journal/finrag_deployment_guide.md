# 🚀 FinRAG Deployment Guide

Deploying a Full-Stack application like FinRAG (React Frontend, FastAPI Backend, SQLite Database) requires hosting the frontend and backend on two separate services, and handling the database storage carefully.

Here is the easiest, most cost-effective way to deploy this project for a portfolio.

---

## 🏗️ The Deployment Architecture

1. **Frontend (React + Vite):** Hosted on **Vercel** or **Netlify** (Free, lightning-fast, native React support).
2. **Backend (FastAPI + Python):** Hosted on **Render**, **Railway**, or **Fly.io** (Free tiers available, native Python support).
3. **Database (SQLite -> PostgreSQL):** Hosted on **Supabase** or **Neon** (Free managed PostgreSQL).

---

## ⚠️ The SQLite Deployment Trap (Crucial Interview Knowledge)

Right now, FinRAG uses **SQLite** (`finrag.db`). SQLite is a *file-based* database.
Free hosting platforms like Render and Heroku use **Ephemeral File Systems**. This means every time your server goes to sleep or restarts, **they wipe the hard drive clean**. 

If you deploy SQLite to Render for free, your PDFs and Vector Embeddings will be deleted every day.

### Solution:
You have two choices:
1. **The Easy Paid Way:** Pay Render ~$7/month for a "Persistent Disk". This guarantees `finrag.db` is never deleted.
2. **The Professional Free Way:** Because we used SQLAlchemy (an ORM), you can migrate to PostgreSQL by changing exactly ONE line of code. Sign up for a free PostgreSQL database on **Supabase** or **Neon**, copy the connection string, and paste it into your `.env` file.

---

## 🛠️ Step-by-Step Deployment

### Step 1: Prepare the Backend (`/backend`)
1. Create a `requirements.txt` file (already done). This tells the hosting provider which Python packages to install.
2. Ensure you have a `Procfile` or a Render start command ready. The command to start the server in production is exactly the same as local: 
   `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
3. Make sure CORS is configured to accept traffic from your future Vercel URL, not just `localhost:5173`. (In `main.py`, under `allow_origins`).

### Step 2: Deploy Backend to Render (render.com)
1. Push your code to GitHub.
2. Go to Render.com -> Click **New Web Service**.
3. Connect your GitHub repository.
4. Set the Environment to **Python 3**.
5. Set the Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
6. Add your Environment Variables in the Render dashboard:
   - `GEMINI_API_KEY=your_google_ai_key`
   - `DATABASE_URL=your_postgres_url` (If using Supabase/Neon, or leave blank to test with ephemeral SQLite)
7. Click Deploy. Render will give you a live URL like `https://finrag-api.onrender.com`.

### Step 3: Prepare the Frontend (`/frontend`)
1. In your React code, you are currently using absolute URLs pointing to localhost: `fetch('http://localhost:8000/api/documents')`.
2. Change the Base URL in `client.js` to use an environment variable so it dynamically points to your live Render backend in production:
   ```javascript
   const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
   ```

### Step 4: Deploy Frontend to Vercel (vercel.com)
1. Go to Vercel.com -> Click **Add New Project**.
2. Connect your GitHub repository.
3. Vercel will automatically detect that it is a Vite/React project.
4. **Crucial:** Set the Root Directory to `frontend`. (Vercel needs to know the React app isn't at the root of the repo).
5. Add Environment Variables:
   - `VITE_API_URL=https://finrag-api.onrender.com` (Your live Render backend URL).
6. Click Deploy. Vercel will give you a live URL like `https://finrag-ui.vercel.app`.

---

## 📈 Final Polish

- **Cold Starts:** Free tiers on Render go to sleep after 15 minutes of inactivity. When a recruiter clicks your link, the *first* query might take 30-50 seconds because the Render backend is waking up (loading Python, loading the Embedding model). You can prevent this by using a cron job service (like cron-job.org) to ping your API every 10 minutes to keep it awake.
- **Data Pre-loading:** Once live, use your newly deployed Vercel frontend to upload 3-4 interesting PDFs (like NVIDIA or Apple 10-Ks) so recruiters don't arrive to an empty dashboard.
