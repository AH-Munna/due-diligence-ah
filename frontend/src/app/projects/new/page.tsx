"use client";

import {
    createProject,
    Document,
    fetchDocuments,
    fetchSampleQuestions,
    SampleSection,
} from "@/lib/api";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function NewProjectPage() {
    const router = useRouter();
    const [name, setName] = useState("");
    const [description, setDescription] = useState("");
    const [sections, setSections] = useState<SampleSection[]>([]);
    const [documents, setDocuments] = useState<Document[]>([]);
    const [selectedQuestions, setSelectedQuestions] = useState<Set<string>>(new Set());
    const [loading, setLoading] = useState(true);
    const [creating, setCreating] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function loadData() {
            try {
                const [questionsData, docsData] = await Promise.all([
                    fetchSampleQuestions(),
                    fetchDocuments(),
                ]);
                setSections(questionsData.sections);
                setDocuments(docsData);
            } catch (err) {
                setError(err instanceof Error ? err.message : "Failed to load data");
            } finally {
                setLoading(false);
            }
        }
        loadData();
    }, []);

    const toggleQuestion = (id: string) => {
        const newSet = new Set(selectedQuestions);
        if (newSet.has(id)) {
            newSet.delete(id);
        } else {
            newSet.add(id);
        }
        setSelectedQuestions(newSet);
    };

    const selectAllInSection = (section: SampleSection) => {
        const newSet = new Set(selectedQuestions);
        section.questions.forEach((q) => newSet.add(q.id));
        setSelectedQuestions(newSet);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!name.trim()) {
            setError("Project name is required");
            return;
        }
        if (selectedQuestions.size === 0) {
            setError("Please select at least one question");
            return;
        }

        setCreating(true);
        setError(null);

        try {
            const project = await createProject({
                name: name.trim(),
                description: description.trim(),
                question_ids: Array.from(selectedQuestions),
            });
            router.push(`/projects/${project.id}`);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to create project");
            setCreating(false);
        }
    };

    const indexedDocs = documents.filter((d) => d.status === "INDEXED");

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
            {/* Header */}
            <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
                    <div className="flex items-center gap-4">
                        <Link href="/" className="text-gray-500 hover:text-gray-700 dark:text-gray-400">
                            ← Back
                        </Link>
                        <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                            New Project
                        </h1>
                    </div>
                </div>
            </header>

            <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {error && (
                    <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300">
                        {error}
                    </div>
                )}

                {indexedDocs.length === 0 && (
                    <div className="mb-6 p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg text-yellow-700 dark:text-yellow-300">
                        ⚠️ No documents indexed yet.{" "}
                        <Link href="/documents" className="underline font-medium">
                            Upload documents first
                        </Link>{" "}
                        to generate answers.
                    </div>
                )}

                <form onSubmit={handleSubmit}>
                    {/* Project Details */}
                    <div className="card p-6 mb-6">
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                            Project Details
                        </h2>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    Project Name *
                                </label>
                                <input
                                    type="text"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    placeholder="e.g., MiniMax Due Diligence Q1 2026"
                                    className="input"
                                    required
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    Description
                                </label>
                                <textarea
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    placeholder="Optional description of this project..."
                                    className="input"
                                    rows={3}
                                />
                            </div>
                        </div>
                    </div>

                    {/* Question Selection */}
                    <div className="card p-6 mb-6">
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                                Select Questions
                            </h2>
                            <span className="text-sm text-gray-500 dark:text-gray-400">
                                {selectedQuestions.size} selected
                            </span>
                        </div>

                        <div className="space-y-6">
                            {sections.map((section) => (
                                <div key={section.name} className="border-b border-gray-200 dark:border-gray-700 pb-4 last:border-0">
                                    <div className="flex items-center justify-between mb-3">
                                        <h3 className="font-medium text-gray-900 dark:text-white">
                                            {section.name}
                                        </h3>
                                        <button
                                            type="button"
                                            onClick={() => selectAllInSection(section)}
                                            className="text-sm text-blue-600 hover:text-blue-700"
                                        >
                                            Select All
                                        </button>
                                    </div>
                                    <div className="space-y-2">
                                        {section.questions.map((q) => (
                                            <label
                                                key={q.id}
                                                className="flex items-start gap-3 p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer"
                                            >
                                                <input
                                                    type="checkbox"
                                                    checked={selectedQuestions.has(q.id)}
                                                    onChange={() => toggleQuestion(q.id)}
                                                    className="mt-1 h-4 w-4 text-blue-600 rounded border-gray-300"
                                                />
                                                <div>
                                                    <div className="text-gray-900 dark:text-white">{q.text}</div>
                                                    <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                                        Type: {q.type}
                                                    </div>
                                                </div>
                                            </label>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Submit */}
                    <div className="flex justify-end gap-4">
                        <Link href="/" className="btn-secondary">
                            Cancel
                        </Link>
                        <button
                            type="submit"
                            disabled={creating || selectedQuestions.size === 0}
                            className="btn-primary"
                        >
                            {creating ? "Creating..." : "Create Project"}
                        </button>
                    </div>
                </form>
            </main>
        </div>
    );
}
