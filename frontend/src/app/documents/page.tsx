"use client";

import {
    deleteDocument,
    Document,
    fetchDocuments,
    uploadDocument,
} from "@/lib/api";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

function formatDate(dateStr: string) {
    return new Date(dateStr).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });
}

function StatusBadge({ status }: { status: string }) {
    const styles: Record<string, string> = {
        INDEXED: "badge-success",
        INDEXING: "badge-info",
        PENDING: "badge-gray",
        FAILED: "badge-error",
    };
    return <span className={`badge ${styles[status] || "badge-gray"}`}>{status}</span>;
}

export default function DocumentsPage() {
    const [documents, setDocuments] = useState<Document[]>([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const loadDocuments = async () => {
        try {
            const data = await fetchDocuments();
            setDocuments(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load documents");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadDocuments();
    }, []);

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        if (!file.name.toLowerCase().endsWith(".pdf")) {
            setError("Only PDF files are supported");
            return;
        }

        setUploading(true);
        setError(null);
        setSuccess(null);

        try {
            const doc = await uploadDocument(file);
            setSuccess(`Successfully indexed "${doc.filename}" (${doc.chunk_count} chunks)`);
            await loadDocuments();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to upload document");
        } finally {
            setUploading(false);
            if (fileInputRef.current) {
                fileInputRef.current.value = "";
            }
        }
    };

    const handleDelete = async (doc: Document) => {
        if (!confirm(`Delete "${doc.filename}"? This will remove all indexed chunks.`)) {
            return;
        }

        try {
            await deleteDocument(doc.id);
            setSuccess(`Deleted "${doc.filename}"`);
            await loadDocuments();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to delete document");
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    const totalPages = documents.reduce((acc, d) => acc + d.page_count, 0);
    const totalChunks = documents.reduce((acc, d) => acc + d.chunk_count, 0);
    const indexedCount = documents.filter((d) => d.status === "INDEXED").length;

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
            {/* Header */}
            <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
                    <div className="flex items-center gap-4 mb-4">
                        <Link href="/" className="text-gray-500 hover:text-gray-700 dark:text-gray-400">
                            ← Back
                        </Link>
                    </div>
                    <div className="flex items-center justify-between">
                        <div>
                            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                                Documents
                            </h1>
                            <p className="text-gray-500 dark:text-gray-400 mt-1">
                                Upload and manage documents for AI analysis
                            </p>
                        </div>
                        <div>
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept=".pdf"
                                onChange={handleUpload}
                                className="hidden"
                                id="file-upload"
                            />
                            <label
                                htmlFor="file-upload"
                                className={`btn-primary cursor-pointer ${uploading ? "opacity-50 cursor-not-allowed" : ""}`}
                            >
                                {uploading ? (
                                    <>
                                        <span className="animate-spin mr-2">⏳</span>
                                        Uploading...
                                    </>
                                ) : (
                                    "📤 Upload PDF"
                                )}
                            </label>
                        </div>
                    </div>
                </div>
            </header>

            <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {error && (
                    <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300 flex justify-between items-center">
                        {error}
                        <button onClick={() => setError(null)} className="text-red-500 hover:text-red-700">
                            ✕
                        </button>
                    </div>
                )}

                {success && (
                    <div className="mb-6 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg text-green-700 dark:text-green-300 flex justify-between items-center">
                        ✓ {success}
                        <button onClick={() => setSuccess(null)} className="text-green-500 hover:text-green-700">
                            ✕
                        </button>
                    </div>
                )}

                {/* Stats */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                    <div className="card p-6">
                        <div className="text-sm text-gray-500 dark:text-gray-400">Total Documents</div>
                        <div className="text-3xl font-bold text-gray-900 dark:text-white mt-1">
                            {indexedCount} / {documents.length}
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">indexed</div>
                    </div>
                    <div className="card p-6">
                        <div className="text-sm text-gray-500 dark:text-gray-400">Total Pages</div>
                        <div className="text-3xl font-bold text-gray-900 dark:text-white mt-1">
                            {totalPages}
                        </div>
                    </div>
                    <div className="card p-6">
                        <div className="text-sm text-gray-500 dark:text-gray-400">Indexed Chunks</div>
                        <div className="text-3xl font-bold text-gray-900 dark:text-white mt-1">
                            {totalChunks}
                        </div>
                    </div>
                </div>

                {/* Document List */}
                <div className="card">
                    <div className="p-6 border-b border-gray-200 dark:border-gray-700">
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                            Uploaded Documents
                        </h2>
                    </div>

                    {documents.length === 0 ? (
                        <div className="p-12 text-center">
                            <div className="text-gray-400 dark:text-gray-500 text-5xl mb-4">📄</div>
                            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                                No documents yet
                            </h3>
                            <p className="text-gray-500 dark:text-gray-400 mb-4">
                                Upload PDF documents to start indexing for AI analysis.
                            </p>
                        </div>
                    ) : (
                        <div className="divide-y divide-gray-200 dark:divide-gray-700">
                            {documents.map((doc) => (
                                <div key={doc.id} className="p-6 flex items-center justify-between">
                                    <div className="flex items-center gap-4">
                                        <div className="text-3xl">📄</div>
                                        <div>
                                            <div className="flex items-center gap-2">
                                                <h3 className="font-medium text-gray-900 dark:text-white">
                                                    {doc.filename}
                                                </h3>
                                                <StatusBadge status={doc.status} />
                                            </div>
                                            <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                                                {doc.page_count} pages • {doc.chunk_count} chunks
                                                {doc.indexed_at && ` • Indexed ${formatDate(doc.indexed_at)}`}
                                            </div>
                                            {doc.error_message && (
                                                <div className="text-sm text-red-600 dark:text-red-400 mt-1">
                                                    Error: {doc.error_message}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => handleDelete(doc)}
                                        className="text-gray-400 hover:text-red-600 transition-colors"
                                        title="Delete document"
                                    >
                                        🗑️
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </main>
        </div>
    );
}
