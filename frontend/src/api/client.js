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

// ── Streaming RAG Q&A (with Chat History) ───
export async function askQuestionStream(question, filters = {}, history = [], callbacks = {}) {
    const { onSources, onToken, onDone, onError } = callbacks;

    try {
        const response = await fetch(`${API_BASE}/ask/stream`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                question,
                history,
                top_k: filters.top_k || 5,
                company: filters.company || null,
                year: filters.year || null,
                region: filters.region || null,
            }),
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop(); // Keep incomplete line in buffer

            for (const line of lines) {
                if (line.startsWith("data: ")) {
                    try {
                        const event = JSON.parse(line.slice(6));
                        if (event.type === "sources" && onSources) {
                            onSources(event.sources, event.retrieval_time);
                        } else if (event.type === "token" && onToken) {
                            onToken(event.token);
                        } else if (event.type === "done" && onDone) {
                            onDone(event.total_time, event.generation_time);
                        }
                    } catch (e) {
                        // Skip malformed JSON lines
                    }
                }
            }
        }
    } catch (error) {
        if (error.message === "Failed to fetch") {
            onError?.("Cannot connect to API. Is the backend running on port 8000?");
        } else {
            onError?.(error.message);
        }
    }
}
