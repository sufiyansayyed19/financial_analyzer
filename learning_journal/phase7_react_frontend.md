# 📓 Phase 7 Learning Journal — React Frontend

**Date:** February 22, 2026
**Duration:** ~30 minutes
**Result:** ✅ Full-stack web app — React dashboard connects to FastAPI backend

---

## 🗂️ Files Created

| # | File | Purpose |
|---|------|---------|
| 1 | `frontend/src/api/client.js` | Fetch wrappers for all API endpoints |
| 2 | `frontend/src/App.jsx` | Router + layout with gradient background |
| 3 | `frontend/src/components/Navbar.jsx` | Glassmorphism navigation bar |
| 4 | `frontend/src/pages/Dashboard.jsx` | Stats cards + document table |
| 5 | `frontend/src/pages/AskSearch.jsx` | RAG Q&A + semantic search |
| 6 | `frontend/src/pages/Upload.jsx` | Drag-and-drop PDF upload |
| 7 | `frontend/src/index.css` | Tailwind v3 + custom component classes |
| 8 | `frontend/tailwind.config.js` | Custom dark theme + colors |
| 9 | `frontend/vite.config.js` | Vite 7 + PostCSS fix |

---

## 🧠 Key Concepts Learned

### 1. Vite — Modern Build Tool

**What:** Vite replaces webpack. It's MUCH faster because it uses native ES modules during dev — no bundling needed until production.

**Why Vite over Create React App?**
- CRA is deprecated/unmaintained
- Vite starts in ~300ms vs CRA's ~10-30 seconds
- Hot module replacement (HMR) is instant

### 2. React Router (Client-Side Routing)

```jsx
<BrowserRouter>
  <Routes>
    <Route path="/" element={<Dashboard />} />
    <Route path="/ask" element={<AskSearch />} />
    <Route path="/upload" element={<Upload />} />
  </Routes>
</BrowserRouter>
```

**Key insight:** No page reload when navigating — React swaps components in-place. The URL changes but it's all happening in the browser.

### 3. Tailwind CSS — Utility-First Approach

**Traditional CSS:**
```css
.button { background: blue; padding: 12px; border-radius: 8px; }
```

**Tailwind:**
```jsx
<button className="bg-blue-500 px-4 py-3 rounded-lg">
```

**Why it matters:** No switching between CSS and JSX files. Styles are co-located with the component.

### 4. Glassmorphism Design Pattern

```css
.glass-card {
  @apply bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl;
}
```

**What:** Semi-transparent, blurred background — gives a "frosted glass" effect. Modern, premium look.

### 5. API Client Pattern (Separation of Concerns)

```
Component → calls client.js → fetch() → Backend API
```

**Why a separate client?** If the API URL changes, we update ONE file. Components don't know about `fetch()`, URLs, or headers.

### 6. CORS in Practice

**Frontend (port 5173) → Backend (port 8000):**
- Without CORS config → Browser blocks the request
- With CORS middleware in FastAPI → Works seamlessly

### 7. Vite 7 + Tailwind v3 Gotcha

**Problem:** Vite 7 uses Lightning CSS by default, which doesn't understand `@tailwind` directives.

**Fix:** Add `css: { transformer: 'postcss' }` to `vite.config.js`.

**Lesson:** Always check compatibility between tool versions.

---

## 📊 Architecture Overview

```
Browser (localhost:5173)         Server (localhost:8000)
┌─────────────────────┐         ┌──────────────────────┐
│  React + Tailwind   │───API──→│  FastAPI              │
│  ├── Dashboard      │         │  ├── /api/health      │
│  ├── Ask & Search   │         │  ├── /api/ask         │
│  └── Upload         │         │  ├── /api/search      │
│                     │         │  ├── /api/documents   │
│  client.js → fetch()│         │  └── /api/upload      │
└─────────────────────┘         └──────────────────────┘
```

---

## 💡 Interview Talking Points

> "For the frontend, I built a React dashboard with Vite and Tailwind CSS. The UI has three main views: a Dashboard showing document stats and a management table, an Ask & Search page for RAG Q&A with company/year filters, and a PDF Upload page with drag-and-drop.
>
> The design uses glassmorphism — semi-transparent cards with backdrop blur on a dark gradient background. I built a centralized API client module so all backend communication goes through one file.
>
> One interesting challenge was Vite 7's default Lightning CSS engine not supporting Tailwind's `@tailwind` directives — I had to explicitly configure PostCSS as the CSS transformer."

---

## ➡️ How to Run

```bash
# Terminal 1: Backend
venv\Scripts\uvicorn backend.main:app --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev
```

Then open **http://localhost:5173** in your browser.
