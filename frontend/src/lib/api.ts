/**
 * API client for the Due Diligence backend
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Types
export interface Document {
  id: string;
  filename: string;
  status: "PENDING" | "INDEXING" | "INDEXED" | "FAILED";
  page_count: number;
  chunk_count: number;
  error_message: string;
  indexed_at: string | null;
  created_at: string;
}

export interface Citation {
  doc_id: string;
  doc_name: string;
  page: number;
  text: string;
  chunk_id: string;
  num?: number;
}

export interface Answer {
  id: string;
  question_id: string;
  ai_answer: string;
  manual_answer: string;
  citations: Citation[];
  confidence: number;
  is_answerable: string;
  status: "PENDING" | "GENERATED" | "CONFIRMED" | "REJECTED" | "MANUAL";
  created_at: string;
}

export interface Question {
  id: string;
  section: string;
  question_text: string;
  order_index: number;
  answer: Answer | null;
}

export interface Project {
  id: string;
  name: string;
  description: string;
  status: "DRAFT" | "READY" | "OUTDATED";
  created_at: string;
  updated_at: string;
  questions: Question[];
}

export interface ProjectListItem {
  id: string;
  name: string;
  status: string;
  question_count: number;
  answered_count: number;
  created_at: string;
}

export interface SampleQuestion {
  id: string;
  text: string;
  type: string;
}

export interface SampleSection {
  name: string;
  questions: SampleQuestion[];
}

export interface SampleQuestionsResponse {
  sections: SampleSection[];
}

// API Functions

export async function fetchDocuments(): Promise<Document[]> {
  const res = await fetch(`${API_BASE}/api/documents`);
  if (!res.ok) throw new Error("Failed to fetch documents");
  return res.json();
}

export async function uploadDocument(file: File): Promise<Document> {
  const formData = new FormData();
  formData.append("file", file);
  
  const res = await fetch(`${API_BASE}/api/documents/upload`, {
    method: "POST",
    body: formData,
  });
  
  if (!res.ok) throw new Error("Failed to upload document");
  return res.json();
}

export async function deleteDocument(docId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/documents/${docId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete document");
}

export async function fetchProjects(): Promise<ProjectListItem[]> {
  const res = await fetch(`${API_BASE}/api/projects`);
  if (!res.ok) throw new Error("Failed to fetch projects");
  return res.json();
}

export async function fetchProject(id: string): Promise<Project> {
  const res = await fetch(`${API_BASE}/api/projects/${id}`);
  if (!res.ok) throw new Error("Failed to fetch project");
  return res.json();
}

export async function fetchSampleQuestions(): Promise<SampleQuestionsResponse> {
  const res = await fetch(`${API_BASE}/api/projects/sample-questions`);
  if (!res.ok) throw new Error("Failed to fetch sample questions");
  return res.json();
}

export async function createProject(data: {
  name: string;
  description: string;
  question_ids: string[];
}): Promise<Project> {
  const res = await fetch(`${API_BASE}/api/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create project");
  return res.json();
}

export async function deleteProject(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/projects/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete project");
}

export async function generateAllAnswers(projectId: string): Promise<{
  project_id: string;
  total: number;
  generated: number;
  errors: { question_id: string; error: string }[];
}> {
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/generate`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to generate answers");
  return res.json();
}

export async function generateSingleAnswer(questionId: string): Promise<Answer> {
  const res = await fetch(`${API_BASE}/api/answers/${questionId}/generate`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to generate answer");
  return res.json();
}

export async function updateAnswer(
  answerId: string,
  data: { status: string; manual_answer?: string }
): Promise<Answer> {
  const res = await fetch(`${API_BASE}/api/answers/${answerId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update answer");
  return res.json();
}
