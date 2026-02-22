/**
 * 🧠 FinRAG — API Client
 * 
 * Central place for ALL backend API calls.
 * Every component uses these functions instead of calling fetch() directly.
 */

const API_BASE = "http://localhost:8000/api";

/**
 * Generic fetch wrapper with error handling.
 */
async function request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;

    try {
        const response = await fetch(url, {
            headers: { "Content-Type": "application/json" },
            ...options,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        if (error.message === "Failed to fetch") {
            throw new Error("Cannot connect to API. Is the backend running on port 8000?");
        }
        throw error;
    }
}

// ── Health ──────────────────────────────────
export async function getHealth() {
    return request("/health");
}

// ── Documents ───────────────────────────────
export async function getDocuments() {
    return request("/documents");
}

export async function deleteDocument(id) {
    return request(`/documents/${id}`, { method: "DELETE" });
}

export async function uploadPDF(file) {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_BASE}/upload`, {
        method: "POST",
        body: formData,
        // No Content-Type header — browser sets it with boundary for multipart
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || `Upload failed: HTTP ${response.status}`);
    }

    return await response.json();
}

// ── Search ──────────────────────────────────
export async function searchDocuments(query, filters = {}) {
    return request("/search", {
        method: "POST",
        body: JSON.stringify({
            query,
            top_k: filters.top_k || 5,
            company: filters.company || null,
            year: filters.year || null,
            region: filters.region || null,
        }),
    });
}

// ── RAG Q&A ─────────────────────────────────
export async function askQuestion(question, filters = {}) {
    return request("/ask", {
        method: "POST",
        body: JSON.stringify({
            question,
            top_k: filters.top_k || 5,
            company: filters.company || null,
            year: filters.year || null,
            region: filters.region || null,
        }),
    });
}
