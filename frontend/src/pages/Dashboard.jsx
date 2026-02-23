import { useState, useEffect } from 'react'
import { getHealth, getDocuments, deleteDocument } from '../api/client'

function Dashboard() {
    const [health, setHealth] = useState(null)
    const [documents, setDocuments] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [deleting, setDeleting] = useState(null)

    useEffect(() => {
        loadData()
    }, [])

    async function loadData() {
        try {
            setLoading(true)
            setError(null)
            const [healthData, docsData] = await Promise.all([
                getHealth(),
                getDocuments(),
            ])
            setHealth(healthData)
            setDocuments(docsData)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    async function handleDelete(id, fileName) {
        if (!confirm(`Delete "${fileName}" and all its chunks?`)) return

        try {
            setDeleting(id)
            await deleteDocument(id)
            setDocuments(prev => prev.filter(d => d.id !== id))
            // Refresh health stats
            const healthData = await getHealth()
            setHealth(healthData)
        } catch (err) {
            alert(`Failed to delete: ${err.message}`)
        } finally {
            setDeleting(null)
        }
    }

    if (loading) {
        return (
            <div className="space-y-8">
                {/* Skeleton header */}
                <div>
                    <div className="skeleton w-48 h-8 mb-2" />
                    <div className="skeleton w-72 h-4" />
                </div>
                {/* Skeleton stats */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {[1, 2, 3, 4].map(i => (
                        <div key={i} className="glass-card p-5 space-y-2">
                            <div className="skeleton w-16 h-3" />
                            <div className="skeleton w-24 h-7" />
                        </div>
                    ))}
                </div>
                {/* Skeleton table */}
                <div className="glass-card p-5 space-y-3">
                    <div className="skeleton w-32 h-5 mb-4" />
                    {[1, 2, 3].map(i => (
                        <div key={i} className="skeleton w-full h-10" />
                    ))}
                </div>
            </div>
        )
    }

    if (error) {
        return (
            <div className="glass-card p-8 text-center">
                <p className="text-red-400 text-lg mb-2">⚠️ Connection Error</p>
                <p className="text-gray-400 text-sm mb-4">{error}</p>
                <button onClick={loadData} className="btn-primary text-sm">
                    Retry
                </button>
            </div>
        )
    }

    // Group documents by company
    const grouped = documents.reduce((acc, doc) => {
        const company = doc.company.charAt(0).toUpperCase() + doc.company.slice(1)
        if (!acc[company]) acc[company] = []
        acc[company].push(doc)
        return acc
    }, {})

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="animate-fade-in-up">
                <h1 className="text-3xl font-bold gradient-text">Dashboard</h1>
                <p className="text-gray-400 mt-1">Your financial document knowledge base</p>
            </div>

            {/* Stats Row */}
            {health && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <StatCard label="Status" value={health.status === 'healthy' ? '🟢 Online' : '🔴 Offline'} delay={1} />
                    <StatCard label="Documents" value={health.total_documents} delay={2} />
                    <StatCard label="Total Chunks" value={health.total_chunks.toLocaleString()} delay={3} />
                    <StatCard label="Companies" value={Object.keys(grouped).length} delay={4} />
                </div>
            )}

            {/* Documents Table */}
            <div className="glass-card overflow-hidden animate-fade-in-up stagger-5">
                <div className="p-5 border-b border-white/10 flex items-center justify-between">
                    <h2 className="text-lg font-semibold text-gray-200">📄 Documents</h2>
                    <span className="text-sm text-gray-500">{documents.length} files</span>
                </div>

                {documents.length === 0 ? (
                    <div className="p-12 text-center text-gray-500">
                        <p className="text-4xl mb-3">📂</p>
                        <p>No documents yet.</p>
                        <p className="text-sm mt-1">Upload PDFs to get started</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="text-left text-xs text-gray-500 uppercase tracking-wider border-b border-white/5">
                                    <th className="px-5 py-3">Company</th>
                                    <th className="px-5 py-3">Year</th>
                                    <th className="px-5 py-3">Region</th>
                                    <th className="px-5 py-3">Chunks</th>
                                    <th className="px-5 py-3">File</th>
                                    <th className="px-5 py-3 text-right">Action</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5">
                                {documents.map((doc) => (
                                    <tr key={doc.id} className="hover:bg-white/[0.02] transition-colors">
                                        <td className="px-5 py-3.5">
                                            <span className="font-medium text-gray-200 capitalize">{doc.company}</span>
                                        </td>
                                        <td className="px-5 py-3.5">
                                            <span className="text-brand-300">{doc.year}</span>
                                        </td>
                                        <td className="px-5 py-3.5">
                                            <span className="text-gray-400 uppercase text-sm">{doc.region}</span>
                                        </td>
                                        <td className="px-5 py-3.5">
                                            <span className="text-gray-300">{doc.total_chunks.toLocaleString()}</span>
                                        </td>
                                        <td className="px-5 py-3.5">
                                            <span className="text-gray-500 text-sm font-mono">{doc.file_name}</span>
                                        </td>
                                        <td className="px-5 py-3.5 text-right">
                                            <button
                                                onClick={() => handleDelete(doc.id, doc.file_name)}
                                                disabled={deleting === doc.id}
                                                className="btn-danger"
                                            >
                                                {deleting === doc.id ? 'Deleting...' : 'Delete'}
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    )
}

function StatCard({ label, value, delay = 0 }) {
    return (
        <div className={`stat-card animate-fade-in-up stagger-${delay}`}>
            <span className="text-xs text-gray-500 uppercase tracking-wider">{label}</span>
            <span className="text-2xl font-bold text-gray-100">{value}</span>
        </div>
    )
}

export default Dashboard
