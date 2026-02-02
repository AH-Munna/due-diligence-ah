"use client";

import { Document, fetchDocuments, fetchProjects, ProjectListItem } from "@/lib/api";
import Link from "next/link";
import { useEffect, useState } from "react";

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    DRAFT: "badge-gray",
    READY: "badge-success",
    OUTDATED: "badge-warning",
    INDEXED: "badge-success",
    INDEXING: "badge-info",
    PENDING: "badge-gray",
    FAILED: "badge-error",
  };
  return <span className={`badge ${styles[status] || "badge-gray"}`}>{status}</span>;
}

export default function Dashboard() {
  const [projects, setProjects] = useState<ProjectListItem[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const [projectsData, documentsData] = await Promise.all([
          fetchProjects(),
          fetchDocuments(),
        ]);
        setProjects(projectsData);
        setDocuments(documentsData);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load data");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

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
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                Due Diligence AH
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                AI-Powered Questionnaire Agent
              </p>
            </div>
            <nav className="flex gap-4">
              <Link href="/documents" className="btn-secondary">
                Documents
              </Link>
              <Link href="/projects/new" className="btn-primary">
                + New Project
              </Link>
            </nav>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300">
            {error}
          </div>
        )}

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="card p-6">
            <div className="text-sm text-gray-500 dark:text-gray-400">Total Projects</div>
            <div className="text-3xl font-bold text-gray-900 dark:text-white mt-1">
              {projects.length}
            </div>
          </div>
          <div className="card p-6">
            <div className="text-sm text-gray-500 dark:text-gray-400">Documents Indexed</div>
            <div className="text-3xl font-bold text-gray-900 dark:text-white mt-1">
              {documents.filter((d) => d.status === "INDEXED").length}
            </div>
          </div>
          <div className="card p-6">
            <div className="text-sm text-gray-500 dark:text-gray-400">Total Chunks</div>
            <div className="text-3xl font-bold text-gray-900 dark:text-white mt-1">
              {documents.reduce((acc, d) => acc + d.chunk_count, 0)}
            </div>
          </div>
        </div>

        {/* Projects List */}
        <div className="card">
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Projects</h2>
          </div>

          {projects.length === 0 ? (
            <div className="p-12 text-center">
              <div className="text-gray-400 dark:text-gray-500 text-5xl mb-4">📋</div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                No projects yet
              </h3>
              <p className="text-gray-500 dark:text-gray-400 mb-4">
                Create your first project to start answering due diligence questions.
              </p>
              <Link href="/projects/new" className="btn-primary">
                Create Project
              </Link>
            </div>
          ) : (
            <div className="divide-y divide-gray-200 dark:divide-gray-700">
              {projects.map((project) => (
                <Link
                  key={project.id}
                  href={`/projects/${project.id}`}
                  className="block p-6 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-3">
                        <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                          {project.name}
                        </h3>
                        <StatusBadge status={project.status} />
                      </div>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                        {project.answered_count} / {project.question_count} questions answered •{" "}
                        {formatDate(project.created_at)}
                      </p>
                    </div>
                    <div className="text-gray-400">→</div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Recent Documents */}
        <div className="card mt-8">
          <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Recent Documents
            </h2>
            <Link href="/documents" className="text-blue-600 hover:text-blue-700 text-sm font-medium">
              View All →
            </Link>
          </div>

          {documents.length === 0 ? (
            <div className="p-12 text-center">
              <div className="text-gray-400 dark:text-gray-500 text-5xl mb-4">📄</div>
              <p className="text-gray-500 dark:text-gray-400">
                No documents uploaded yet. Upload documents to start indexing.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200 dark:divide-gray-700">
              {documents.slice(0, 5).map((doc) => (
                <div key={doc.id} className="p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="text-2xl">📄</div>
                    <div>
                      <div className="font-medium text-gray-900 dark:text-white">
                        {doc.filename}
                      </div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        {doc.page_count} pages • {doc.chunk_count} chunks
                      </div>
                    </div>
                  </div>
                  <StatusBadge status={doc.status} />
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
