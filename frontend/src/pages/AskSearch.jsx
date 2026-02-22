import { useState } from 'react'
import { askQuestion, searchDocuments } from '../api/client'

function AskSearch() {
    const [query, setQuery] = useState('')
    const [mode, setMode] = useState('ask') // 'ask' or 'search'
    const [company, setCompany] = useState('')
    const [year, setYear] = useState('')
    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState(null)
    const [error, setError] = useState(null)

    async function handleSubmit(e) {
        e.preventDefault()
        if (!query.trim()) return

        try {
            setLoading(true)
            setError(null)
            setResult(null)

            const filters = {
                company: company || null,
                year: year || null,
                top_k: 5,
            }

            if (mode === 'ask') {
                const response = await askQuestion(query, filters)
                setResult({ type: 'ask', data: response })
            } else {
                const response = await searchDocuments(query, filters)
                setResult({ type: 'search', data: response })
            }
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold gradient-text">Ask & Search</h1>
                <p className="text-gray-400 mt-1">
                    {mode === 'ask'
                        ? 'Ask questions and get AI answers with citations'
                        : 'Search for relevant passages across all documents'}
                </p>
            </div>

            {/* Query Form */}
            <form onSubmit={handleSubmit} className="glass-card p-6 space-y-4">
                {/* Mode Toggle */}
                <div className="flex gap-2">
                    <button
                        type="button"
                        onClick={() => { setMode('ask'); setResult(null) }}
                        className={`px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${mode === 'ask'
                                ? 'bg-brand-600/20 text-brand-300 border border-brand-500/30'
                                : 'text-gray-400 hover:text-gray-200 hover:bg-white/5 border border-transparent'
                            }`}
                    >
                        🤖 Ask AI
                    </button>
                    <button
                        type="button"
                        onClick={() => { setMode('search'); setResult(null) }}
                        className={`px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${mode === 'search'
                                ? 'bg-brand-600/20 text-brand-300 border border-brand-500/30'
                                : 'text-gray-400 hover:text-gray-200 hover:bg-white/5 border border-transparent'
                            }`}
                    >
                        🔍 Search
                    </button>
                </div>

                {/* Input */}
                <div className="relative">
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder={mode === 'ask'
                            ? "What was NVIDIA's revenue in 2024?"
                            : "Search for revenue, risk factors, dividends..."}
                        className="input-field pr-24 text-lg"
                    />
                    <button
                        type="submit"
                        disabled={loading || !query.trim()}
                        className="absolute right-2 top-1/2 -translate-y-1/2 btn-primary py-2 px-4 text-sm"
                    >
                        {loading ? (
                            <span className="flex items-center gap-2">
                                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                {mode === 'ask' ? 'Thinking...' : 'Searching...'}
                            </span>
                        ) : (
                            mode === 'ask' ? 'Ask' : 'Search'
                        )}
                    </button>
                </div>

                {/* Filters */}
                <div className="flex gap-3 flex-wrap">
                    <select
                        value={company}
                        onChange={(e) => setCompany(e.target.value)}
                        className="filter-select"
                    >
                        <option value="">All Companies</option>
                        <option value="nvidia">NVIDIA</option>
                        <option value="tesla">Tesla</option>
                        <option value="apple">Apple</option>
                        <option value="microsoft">Microsoft</option>
                        <option value="jpmorgan">JPMorgan</option>
                        <option value="goldmansachs">Goldman Sachs</option>
                        <option value="reliance">Reliance</option>
                        <option value="tcs">TCS</option>
                        <option value="infosys">Infosys</option>
                        <option value="hdfc">HDFC</option>
                    </select>
                    <select
                        value={year}
                        onChange={(e) => setYear(e.target.value)}
                        className="filter-select"
                    >
                        <option value="">All Years</option>
                        <option value="2024">2024</option>
                        <option value="2023">2023</option>
                        <option value="2022">2022</option>
                    </select>
                </div>
            </form>

            {/* Error */}
            {error && (
                <div className="glass-card p-4 border-red-500/30">
                    <p className="text-red-400">⚠️ {error}</p>
                </div>
            )}

            {/* Results */}
            {result?.type === 'ask' && <AskResult data={result.data} />}
            {result?.type === 'search' && <SearchResults data={result.data} />}
        </div>
    )
}


function AskResult({ data }) {
    return (
        <div className="space-y-4">
            {/* Answer Card */}
            <div className="glass-card p-6">
                <div className="flex items-center gap-2 mb-4">
                    <span className="text-brand-400 text-lg">🤖</span>
                    <h3 className="text-lg font-semibold text-gray-200">AI Answer</h3>
                    <span className="ml-auto text-xs text-gray-500">{data.total_time.toFixed(1)}s</span>
                </div>

                <div className="prose prose-invert max-w-none">
                    <p className="text-gray-300 leading-relaxed whitespace-pre-wrap">{data.answer}</p>
                </div>
            </div>

            {/* Timing */}
            <div className="flex gap-3 text-xs text-gray-500">
                <span>🔍 Search: {data.retrieval_time.toFixed(1)}s</span>
                <span>•</span>
                <span>🤖 Generate: {data.generation_time.toFixed(1)}s</span>
                <span>•</span>
                <span>📚 {data.chunks_searched.toLocaleString()} chunks searched</span>
            </div>

            {/* Sources */}
            {data.sources.length > 0 && (
                <div className="space-y-2">
                    <h4 className="text-sm font-medium text-gray-400">📚 Sources</h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                        {data.sources.map((source) => (
                            <SourceCard key={source.source_id} source={source} />
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}

function SourceCard({ source }) {
    const [expanded, setExpanded] = useState(false)
    const scorePercent = Math.round(source.relevance_score * 100)
    const scoreColor = scorePercent >= 65 ? 'text-green-400' : scorePercent >= 50 ? 'text-yellow-400' : 'text-gray-400'

    return (
        <div
            className="glass-card-hover p-4 cursor-pointer"
            onClick={() => setExpanded(!expanded)}
        >
            <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-brand-300">
                    [Source {source.source_id}]
                </span>
                <span className={`text-xs font-mono ${scoreColor}`}>
                    {scorePercent}% match
                </span>
            </div>
            <p className="text-xs text-gray-400 capitalize">
                {source.company} • {source.year} • {source.region}
            </p>
            {expanded && source.chunk_preview && (
                <p className="text-xs text-gray-500 mt-2 border-t border-white/5 pt-2 line-clamp-4">
                    {source.chunk_preview}
                </p>
            )}
        </div>
    )
}


function SearchResults({ data }) {
    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-200">
                    🔍 Search Results
                </h3>
                <span className="text-sm text-gray-500">
                    {data.total_results} results
                </span>
            </div>

            {data.results.length === 0 ? (
                <div className="glass-card p-8 text-center text-gray-500">
                    No results found. Try different keywords.
                </div>
            ) : (
                data.results.map((result, i) => (
                    <SearchResultCard key={i} result={result} index={i + 1} />
                ))
            )}
        </div>
    )
}

function SearchResultCard({ result, index }) {
    const scorePercent = Math.round(result.score * 100)
    const scoreColor = scorePercent >= 65 ? 'text-green-400' : scorePercent >= 50 ? 'text-yellow-400' : 'text-gray-400'

    return (
        <div className="glass-card p-5">
            <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                    <span className="text-xs bg-white/10 text-gray-400 px-2 py-0.5 rounded-md font-mono">
                        #{index}
                    </span>
                    <span className="text-sm text-gray-300 capitalize font-medium">
                        {result.company} • {result.year}
                    </span>
                </div>
                <span className={`text-sm font-mono ${scoreColor}`}>
                    {scorePercent}%
                </span>
            </div>
            <p className="text-sm text-gray-400 leading-relaxed">{result.text}</p>
        </div>
    )
}

export default AskSearch
