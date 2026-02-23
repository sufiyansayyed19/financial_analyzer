import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import { askQuestionStream, searchDocuments, getDocuments } from '../api/client'

function AskSearch() {
    const [query, setQuery] = useState('')
    const [mode, setMode] = useState('ask') // 'ask' or 'search'
    const [company, setCompany] = useState('')
    const [year, setYear] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)
    const [docs, setDocs] = useState([])

    // Chat history state
    const [messages, setMessages] = useState([]) // {role, content, sources?, timing?}
    const [streamingText, setStreamingText] = useState('')
    const [streamingSources, setStreamingSources] = useState(null)
    const [isStreaming, setIsStreaming] = useState(false)

    // Search mode state
    const [searchResult, setSearchResult] = useState(null)

    const chatEndRef = useRef(null)

    // Fetch documents on mount to populate filters
    useEffect(() => {
        getDocuments()
            .then(data => setDocs(data))
            .catch(err => console.error("Failed to load documents for filters:", err))
    }, [])

    // Auto-scroll to bottom when new messages arrive
    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages, streamingText])

    // Derive unique companies dynamically
    const availableCompanies = [...new Set(docs.map(d => d.company))].sort()
    const availableYears = [...new Set(
        docs
            .filter(d => !company || d.company === company)
            .map(d => d.year)
    )].sort((a, b) => b.localeCompare(a))

    async function handleSubmit(e) {
        e.preventDefault()
        if (!query.trim()) return

        if (mode === 'search') {
            handleSearch()
            return
        }

        // ASK mode — streaming with chat history
        const userMessage = query.trim()
        setQuery('')
        setError(null)
        setLoading(true)
        setIsStreaming(true)
        setStreamingText('')
        setStreamingSources(null)

        // Add user message to chat
        setMessages(prev => [...prev, { role: 'user', content: userMessage }])

        // Build history for the API (previous messages only)
        const history = messages.map(m => ({
            role: m.role,
            content: m.content,
        }))

        const filters = {
            company: company || null,
            year: year || null,
            top_k: 5,
        }

        let fullAnswer = ''
        let sources = []
        let timing = {}

        await askQuestionStream(userMessage, filters, history, {
            onSources: (s, retrievalTime) => {
                sources = s
                setStreamingSources(s)
            },
            onToken: (token) => {
                fullAnswer += token
                setStreamingText(prev => prev + token)
            },
            onDone: (totalTime, generationTime) => {
                timing = { totalTime, generationTime }
            },
            onError: (errMsg) => {
                setError(errMsg)
            },
        })

        // Add assistant message to chat history
        setMessages(prev => [...prev, {
            role: 'assistant',
            content: fullAnswer,
            sources,
            timing,
        }])

        setStreamingText('')
        setStreamingSources(null)
        setIsStreaming(false)
        setLoading(false)
    }

    async function handleSearch() {
        try {
            setLoading(true)
            setError(null)
            setSearchResult(null)
            const response = await searchDocuments(query, {
                company: company || null,
                year: year || null,
                top_k: 5,
            })
            setSearchResult(response)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    function clearChat() {
        setMessages([])
        setStreamingText('')
        setStreamingSources(null)
    }

    return (
        <div className="space-y-4">
            {/* Header */}
            <div className="animate-fade-in-up flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold gradient-text">Ask & Search</h1>
                    <p className="text-gray-400 mt-1">
                        {mode === 'ask'
                            ? 'Chat with your financial documents — follow-up questions supported'
                            : 'Search for relevant passages across all documents'}
                    </p>
                </div>
                {mode === 'ask' && messages.length > 0 && (
                    <button onClick={clearChat} className="btn-secondary text-xs">
                        🗑️ Clear Chat
                    </button>
                )}
            </div>

            {/* Mode Toggle + Filters */}
            <div className="glass-card p-4 animate-fade-in-up stagger-1">
                <div className="flex items-center gap-3 flex-wrap">
                    <div className="flex gap-2">
                        <button
                            type="button"
                            onClick={() => { setMode('ask'); setSearchResult(null) }}
                            className={`px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${mode === 'ask'
                                ? 'bg-brand-600/20 text-brand-300 border border-brand-500/30'
                                : 'text-gray-400 hover:text-gray-200 hover:bg-white/5 border border-transparent'
                                }`}
                        >
                            💬 Chat
                        </button>
                        <button
                            type="button"
                            onClick={() => { setMode('search'); setSearchResult(null) }}
                            className={`px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${mode === 'search'
                                ? 'bg-brand-600/20 text-brand-300 border border-brand-500/30'
                                : 'text-gray-400 hover:text-gray-200 hover:bg-white/5 border border-transparent'
                                }`}
                        >
                            🔍 Search
                        </button>
                    </div>

                    <div className="flex gap-2 ml-auto">
                        <select
                            value={company}
                            onChange={(e) => { setCompany(e.target.value); setYear('') }}
                            className="filter-select text-xs"
                        >
                            <option value="">All Companies</option>
                            {availableCompanies.map(c => (
                                <option key={c} value={c}>{c}</option>
                            ))}
                        </select>
                        <select
                            value={year}
                            onChange={(e) => setYear(e.target.value)}
                            className="filter-select text-xs"
                        >
                            <option value="">All Years</option>
                            {availableYears.map(y => (
                                <option key={y} value={y}>{y}</option>
                            ))}
                        </select>
                    </div>
                </div>
            </div>

            {/* Chat Messages Area (Ask mode only) */}
            {mode === 'ask' && (
                <div className="space-y-4 min-h-[200px] max-h-[55vh] overflow-y-auto pr-2">
                    {messages.length === 0 && !isStreaming && (
                        <div className="glass-card p-8 text-center text-gray-500 animate-fade-in">
                            <p className="text-3xl mb-3">💬</p>
                            <p className="text-lg font-medium text-gray-400">Start a conversation</p>
                            <p className="text-sm mt-1">Ask about revenue, risks, financials — follow up naturally</p>
                        </div>
                    )}

                    {/* Rendered messages */}
                    {messages.map((msg, i) => (
                        <ChatBubble key={i} message={msg} />
                    ))}

                    {/* Currently streaming message */}
                    {isStreaming && (
                        <div className="space-y-3 animate-fade-in">
                            {/* Progress bar while searching */}
                            {!streamingSources && (
                                <div className="progress-bar-indeterminate" />
                            )}

                            {/* Streaming answer */}
                            {streamingText && (
                                <div className="flex gap-3">
                                    <div className="w-8 h-8 bg-brand-500/20 rounded-lg flex items-center justify-center flex-shrink-0 mt-1">
                                        <span className="text-sm">🤖</span>
                                    </div>
                                    <div className="glass-card p-4 flex-1">
                                        <div className="markdown-prose typing-cursor">
                                            <ReactMarkdown>{streamingText}</ReactMarkdown>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    <div ref={chatEndRef} />
                </div>
            )}

            {/* Query Input */}
            <form onSubmit={handleSubmit} className="sticky bottom-0 z-10">
                <div className="relative">
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder={mode === 'ask'
                            ? messages.length > 0 ? "Ask a follow-up..." : "What was NVIDIA's revenue in 2024?"
                            : "Search for revenue, risk factors, dividends..."}
                        className="input-field pr-24 text-lg"
                        disabled={isStreaming}
                    />
                    <button
                        type="submit"
                        disabled={loading || !query.trim()}
                        className="absolute right-2 top-1/2 -translate-y-1/2 btn-primary py-2 px-4 text-sm"
                    >
                        {loading ? (
                            <span className="flex items-center gap-2">
                                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                {isStreaming ? 'Streaming...' : 'Searching...'}
                            </span>
                        ) : (
                            mode === 'ask' ? '💬 Send' : '🔍 Search'
                        )}
                    </button>
                </div>
            </form>

            {/* Error */}
            {error && (
                <div className="glass-card p-4 border-red-500/30 animate-scale-in">
                    <p className="text-red-400">⚠️ {error}</p>
                </div>
            )}

            {/* Search Results (Search mode only) */}
            {searchResult && <SearchResults data={searchResult} />}
        </div>
    )
}


/* ─────────────────────────────────────────
   💬 CHAT BUBBLE
   ───────────────────────────────────────── */

function ChatBubble({ message }) {
    const isUser = message.role === 'user'

    return (
        <div className={`flex gap-3 animate-fade-in-up ${isUser ? 'justify-end' : ''}`}>
            {/* Avatar */}
            {!isUser && (
                <div className="w-8 h-8 bg-brand-500/20 rounded-lg flex items-center justify-center flex-shrink-0 mt-1">
                    <span className="text-sm">🤖</span>
                </div>
            )}

            <div className={`max-w-[80%] space-y-2 ${isUser ? 'items-end' : ''}`}>
                {/* Message bubble */}
                <div className={`p-4 rounded-2xl ${isUser
                    ? 'bg-brand-600/20 border border-brand-500/20 rounded-tr-md'
                    : 'glass-card rounded-tl-md'
                    }`}
                >
                    <div className="markdown-prose">
                        <ReactMarkdown>{message.content}</ReactMarkdown>
                    </div>
                </div>

                {/* Sources (assistant only) */}
                {!isUser && message.sources?.length > 0 && (
                    <div className="flex gap-2 flex-wrap">
                        {message.sources.map((s) => (
                            <SourceChip key={s.source_id} source={s} />
                        ))}
                    </div>
                )}

                {/* Timing badge (assistant only) */}
                {!isUser && message.timing?.totalTime && (
                    <span className="text-xs text-gray-600">
                        ⏱ {message.timing.totalTime.toFixed(1)}s
                    </span>
                )}
            </div>

            {/* User avatar */}
            {isUser && (
                <div className="w-8 h-8 bg-white/10 rounded-lg flex items-center justify-center flex-shrink-0 mt-1">
                    <span className="text-sm">👤</span>
                </div>
            )}
        </div>
    )
}


/* ─────────────────────────────────────────
   📎 SOURCE CHIP (compact inline source)
   ───────────────────────────────────────── */

function SourceChip({ source }) {
    const [expanded, setExpanded] = useState(false)
    const scorePercent = Math.round(source.relevance_score * 100)
    const scoreColor = scorePercent >= 65 ? 'text-green-400' : scorePercent >= 50 ? 'text-yellow-400' : 'text-gray-400'

    return (
        <div
            className="glass-card-hover px-2.5 py-1.5 cursor-pointer text-xs inline-flex items-center gap-1.5"
            onClick={() => setExpanded(!expanded)}
        >
            <span className="text-brand-300 font-medium">[{source.source_id}]</span>
            <span className="text-gray-400 capitalize">{source.company}</span>
            <span className="text-gray-600">•</span>
            <span className="text-gray-400">{source.year}</span>
            <span className={`font-mono ${scoreColor}`}>{scorePercent}%</span>

            {expanded && source.chunk_preview && (
                <div className="absolute left-0 top-full mt-1 z-10 glass-card p-3 text-xs text-gray-400 max-w-xs animate-fade-in">
                    {source.chunk_preview}
                </div>
            )}
        </div>
    )
}


/* ─────────────────────────────────────────
   🔍 SEARCH RESULTS
   ───────────────────────────────────────── */

function SearchResults({ data }) {
    return (
        <div className="space-y-3 animate-fade-in-up">
            <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-200">🔍 Search Results</h3>
                <span className="text-sm text-gray-500">{data.total_results} results</span>
            </div>

            {data.results.length === 0 ? (
                <div className="glass-card p-8 text-center text-gray-500">
                    No results found. Try different keywords.
                </div>
            ) : (
                data.results.map((result, i) => (
                    <SearchResultCard key={i} result={result} index={i + 1} delay={i} />
                ))
            )}
        </div>
    )
}

function SearchResultCard({ result, index, delay }) {
    const scorePercent = Math.round(result.score * 100)
    const scoreColor = scorePercent >= 65 ? 'text-green-400' : scorePercent >= 50 ? 'text-yellow-400' : 'text-gray-400'

    return (
        <div className={`glass-card p-5 animate-fade-in-up stagger-${Math.min(delay + 1, 10)}`}>
            <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                    <span className="text-xs bg-white/10 text-gray-400 px-2 py-0.5 rounded-md font-mono">
                        #{index}
                    </span>
                    <span className="text-sm text-gray-300 capitalize font-medium">
                        {result.company} • {result.year}
                    </span>
                </div>
                <span className={`text-sm font-mono ${scoreColor}`}>{scorePercent}%</span>
            </div>
            <p className="text-sm text-gray-400 leading-relaxed">{result.text}</p>
        </div>
    )
}

export default AskSearch
