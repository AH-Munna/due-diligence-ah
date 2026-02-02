"use client";

import {
    deleteProject,
    fetchProject,
    generateAllAnswers,
    Project,
    Question,
    updateAnswer
} from "@/lib/api";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { use, useEffect, useState } from "react";

function StatusBadge({ status }: { status: string }) {
    const styles: Record<string, string> = {
        DRAFT: "badge-gray",
        READY: "badge-success",
        OUTDATED: "badge-warning",
        PENDING: "badge-gray",
        GENERATED: "badge-info",
        CONFIRMED: "badge-success",
        REJECTED: "badge-error",
        MANUAL: "badge-warning",
    };
    return <span className={`badge ${styles[status] || "badge-gray"}`}>{status}</span>;
}

function ConfidenceBadge({ confidence }: { confidence: number }) {
    const pct = Math.round(confidence * 100);
    let color = "text-red-600";
    if (pct >= 80) color = "text-green-600";
    else if (pct >= 50) color = "text-yellow-600";
    return (
        <span className={`text-sm font-medium ${color}`}>
            {pct}% confidence
        </span>
    );
}

interface QuestionCardProps {
    question: Question;
    onRefresh: () => void;
}

function QuestionCard({ question, onRefresh }: QuestionCardProps) {
    const [expanded, setExpanded] = useState(false);
    const [reviewing, setReviewing] = useState(false);
    const [manualAnswer, setManualAnswer] = useState("");
    const [showCitations, setShowCitations] = useState(false);

    const answer = question.answer;

    const handleReview = async (status: "CONFIRMED" | "REJECTED" | "MANUAL") => {
        if (!answer) return;
        setReviewing(true);
        try {
            await updateAnswer(answer.id, {
                status,
                manual_answer: status === "MANUAL" ? manualAnswer : undefined,
            });
            onRefresh();
        } catch (err) {
            console.error(err);
        } finally {
            setReviewing(false);
        }
    };

    return (
        <div className="card p-6">
            <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                        <span className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                            {question.section}
                        </span>
                        {answer && <StatusBadge status={answer.status} />}
                    </div>
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                        {question.question_text}
                    </h3>
                </div>
                <button
                    onClick={() => setExpanded(!expanded)}
                    className="text-gray-400 hover:text-gray-600 text-xl"
                >
                    {expanded ? "−" : "+"}
                </button>
            </div>

            {expanded && (
                <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                    {!answer ? (
                        <div className="text-gray-500 dark:text-gray-400 text-center py-4">
                            No answer generated yet. Click "Generate All Answers" to start.
                        </div>
                    ) : (
                        <>
                            {/* AI Answer */}
                            <div className="mb-4">
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                                        AI Answer
                                    </span>
                                    {answer.confidence !== undefined && (
                                        <ConfidenceBadge confidence={answer.confidence} />
                                    )}
                                </div>
                                <div className="prose prose-sm dark:prose-invert max-w-none bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
                                    {answer.ai_answer.split("\n").map((line, i) => (
                                        <p key={i} className="mb-2 last:mb-0">
                                            {line}
                                        </p>
                                    ))}
                                </div>
                            </div>

                            {/* Manual Answer if exists */}
                            {answer.manual_answer && (
                                <div className="mb-4">
                                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-2">
                                        Manual Answer
                                    </span>
                                    <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-4 border border-yellow-200 dark:border-yellow-800">
                                        {answer.manual_answer}
                                    </div>
                                </div>
                            )}

                            {/* Citations */}
                            {answer.citations.length > 0 && (
                                <div className="mb-4">
                                    <button
                                        onClick={() => setShowCitations(!showCitations)}
                                        className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1"
                                    >
                                        📎 {answer.citations.length} Citations
                                        <span className="text-xs">{showCitations ? "▼" : "▶"}</span>
                                    </button>
                                    {showCitations && (
                                        <div className="mt-2 space-y-2">
                                            {answer.citations.map((citation, i) => (
                                                <div
                                                    key={i}
                                                    className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3 border border-blue-200 dark:border-blue-800 text-sm"
                                                >
                                                    <div className="font-medium text-blue-800 dark:text-blue-200 mb-1">
                                                        📄 {citation.doc_name} - Page {citation.page}
                                                    </div>
                                                    <div className="text-gray-600 dark:text-gray-400 text-xs">
                                                        {citation.text}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Review Actions */}
                            {answer.status === "GENERATED" && (
                                <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                                    <div className="flex flex-wrap gap-2 mb-3">
                                        <button
                                            onClick={() => handleReview("CONFIRMED")}
                                            disabled={reviewing}
                                            className="btn-success"
                                        >
                                            ✓ Confirm
                                        </button>
                                        <button
                                            onClick={() => handleReview("REJECTED")}
                                            disabled={reviewing}
                                            className="btn-danger"
                                        >
                                            ✗ Reject
                                        </button>
                                    </div>
                                    <div className="space-y-2">
                                        <textarea
                                            value={manualAnswer}
                                            onChange={(e) => setManualAnswer(e.target.value)}
                                            placeholder="Enter manual answer override..."
                                            className="input text-sm"
                                            rows={2}
                                        />
                                        <button
                                            onClick={() => handleReview("MANUAL")}
                                            disabled={reviewing || !manualAnswer.trim()}
                                            className="btn-secondary text-sm"
                                        >
                                            Save Manual Answer
                                        </button>
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                </div>
            )}
        </div>
    );
}

export default function ProjectDetailPage({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const resolvedParams = use(params);
    const router = useRouter();
    const [project, setProject] = useState<Project | null>(null);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const loadProject = async () => {
        try {
            const data = await fetchProject(resolvedParams.id);
            setProject(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load project");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadProject();
    }, [resolvedParams.id]);

    const handleGenerateAll = async () => {
        if (!project) return;
        setGenerating(true);
        setError(null);
        try {
            const result = await generateAllAnswers(project.id);
            if (result.errors.length > 0) {
                setError(`Generated ${result.generated}/${result.total}, ${result.errors.length} errors`);
            }
            await loadProject();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to generate answers");
        } finally {
            setGenerating(false);
        }
    };

    const handleDelete = async () => {
        if (!project) return;
        if (!confirm("Are you sure you want to delete this project?")) return;
        try {
            await deleteProject(project.id);
            router.push("/");
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to delete project");
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    if (!project) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center">
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                        Project not found
                    </h1>
                    <Link href="/" className="text-blue-600 hover:text-blue-700">
                        ← Back to Dashboard
                    </Link>
                </div>
            </div>
        );
    }

    const answeredCount = project.questions.filter(
        (q) => q.answer && q.answer.status !== "PENDING"
    ).length;

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
                            <div className="flex items-center gap-3">
                                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                                    {project.name}
                                </h1>
                                <StatusBadge status={project.status} />
                            </div>
                            {project.description && (
                                <p className="text-gray-500 dark:text-gray-400 mt-1">
                                    {project.description}
                                </p>
                            )}
                            <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                                {answeredCount} / {project.questions.length} questions answered
                            </p>
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={handleGenerateAll}
                                disabled={generating}
                                className="btn-primary"
                            >
                                {generating ? (
                                    <>
                                        <span className="animate-spin mr-2">⏳</span>
                                        Generating...
                                    </>
                                ) : (
                                    "🤖 Generate All Answers"
                                )}
                            </button>
                            <button onClick={handleDelete} className="btn-secondary text-red-600">
                                🗑️
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {error && (
                    <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300">
                        {error}
                    </div>
                )}

                {generating && (
                    <div className="mb-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg text-blue-700 dark:text-blue-300">
                        ⏳ Generating answers using AI. This may take a few minutes...
                    </div>
                )}

                {/* Questions */}
                <div className="space-y-4">
                    {project.questions.map((question) => (
                        <QuestionCard
                            key={question.id}
                            question={question}
                            onRefresh={loadProject}
                        />
                    ))}
                </div>
            </main>
        </div>
    );
}
