import { useState, useRef } from 'react'
import { uploadPDF } from '../api/client'

function Upload() {
    const [dragging, setDragging] = useState(false)
    const [uploading, setUploading] = useState(false)
    const [result, setResult] = useState(null)
    const [error, setError] = useState(null)
    const fileRef = useRef()

    function handleDragOver(e) {
        e.preventDefault()
        setDragging(true)
    }

    function handleDragLeave(e) {
        e.preventDefault()
        setDragging(false)
    }

    function handleDrop(e) {
        e.preventDefault()
        setDragging(false)
        const file = e.dataTransfer.files[0]
        if (file) processFile(file)
    }

    function handleFileSelect(e) {
        const file = e.target.files[0]
        if (file) processFile(file)
    }

    async function processFile(file) {
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            setError('Only PDF files are accepted')
            return
        }

        try {
            setUploading(true)
            setError(null)
            setResult(null)
            const response = await uploadPDF(file)
            setResult(response)
        } catch (err) {
            setError(err.message)
        } finally {
            setUploading(false)
            if (fileRef.current) fileRef.current.value = ''
        }
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="animate-fade-in-up">
                <h1 className="text-3xl font-bold gradient-text">Upload Document</h1>
                <p className="text-gray-400 mt-1">
                    Upload a financial PDF to add it to your knowledge base
                </p>
            </div>

            {/* Upload Zone */}
            <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => !uploading && fileRef.current?.click()}
                className={`
          glass-card p-12 text-center cursor-pointer transition-all duration-300 animate-fade-in-up stagger-1
          ${dragging
                        ? 'border-brand-500 bg-brand-500/10 scale-[1.02]'
                        : 'hover:border-white/20 hover:bg-white/[0.03]'
                    }
          ${uploading ? 'pointer-events-none opacity-60' : ''}
        `}
            >
                <input
                    type="file"
                    ref={fileRef}
                    accept=".pdf"
                    onChange={handleFileSelect}
                    className="hidden"
                />

                {uploading ? (
                    <div className="flex flex-col items-center gap-4">
                        <div className="w-12 h-12 border-3 border-brand-500 border-t-transparent rounded-full animate-spin" />
                        <div>
                            <p className="text-lg font-semibold text-gray-200">Processing...</p>
                            <p className="text-sm text-gray-500 mt-1">
                                Extracting → Cleaning → Chunking → Embedding
                            </p>
                        </div>
                        {/* Progress Steps */}
                        <div className="flex gap-6 mt-2 text-xs text-gray-500">
                            <Step label="Extract" active />
                            <Step label="Clean" />
                            <Step label="Chunk" />
                            <Step label="Embed" />
                            <Step label="Store" />
                        </div>
                    </div>
                ) : (
                    <div className="flex flex-col items-center gap-4">
                        <div className="w-16 h-16 bg-brand-500/10 rounded-2xl flex items-center justify-center">
                            <span className="text-3xl">{dragging ? '📥' : '📄'}</span>
                        </div>
                        <div>
                            <p className="text-lg font-semibold text-gray-200">
                                {dragging ? 'Drop your PDF here' : 'Drag & drop a PDF'}
                            </p>
                            <p className="text-sm text-gray-500 mt-1">
                                or click to browse • Financial reports (10-K, Annual, etc.)
                            </p>
                        </div>
                        <div className="flex items-center gap-3 text-xs text-gray-600 mt-2">
                            <span>PDF only</span>
                            <span>•</span>
                            <span>Auto-processed</span>
                            <span>•</span>
                            <span>~30-60s per document</span>
                        </div>
                    </div>
                )}
            </div>

            {/* Naming Guide */}
            <div className="glass-card p-5 animate-fade-in-up stagger-2">
                <h3 className="text-sm font-medium text-gray-400 mb-3">
                    📝 File Naming Convention
                </h3>
                <p className="text-xs text-gray-500 mb-2">
                    Name your PDFs as <code className="text-brand-300 bg-white/5 px-1.5 py-0.5 rounded">company_year_type.pdf</code> for automatic metadata detection:
                </p>
                <div className="flex flex-wrap gap-2">
                    {['nvidia_2024_annual.pdf', 'tesla_2023_10k.pdf', 'reliance_2024_annual.pdf'].map(name => (
                        <span key={name} className="text-xs font-mono text-gray-400 bg-white/5 px-2 py-1 rounded-md">
                            {name}
                        </span>
                    ))}
                </div>
            </div>

            {/* Success */}
            {result && (
                <div className="glass-card p-6 border-green-500/30 animate-scale-in">
                    <div className="flex items-center gap-3 mb-3">
                        <span className="text-2xl">✅</span>
                        <h3 className="text-lg font-semibold text-green-400">Upload Complete!</h3>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                        <div>
                            <p className="text-gray-500">File</p>
                            <p className="text-gray-300 font-mono text-xs mt-1">{result.file_name}</p>
                        </div>
                        <div>
                            <p className="text-gray-500">Document ID</p>
                            <p className="text-gray-300 font-medium mt-1">#{result.document_id}</p>
                        </div>
                        <div>
                            <p className="text-gray-500">Chunks Created</p>
                            <p className="text-gray-300 font-medium mt-1">{result.chunks_created}</p>
                        </div>
                        <div>
                            <p className="text-gray-500">Status</p>
                            <p className="text-green-400 font-medium mt-1">Ready to search</p>
                        </div>
                    </div>
                </div>
            )}

            {/* Error */}
            {error && (
                <div className="glass-card p-5 border-red-500/30 animate-scale-in">
                    <p className="text-red-400">⚠️ {error}</p>
                </div>
            )}
        </div>
    )
}

function Step({ label, active }) {
    return (
        <span className={`${active ? 'text-brand-400 animate-pulse-glow' : ''}`}>
            {label}
        </span>
    )
}

export default Upload
