const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface User {
  id: number;
  username: string;
  email: string;
  role: string;
  full_name?: string;
  department?: string;
}

export interface Citation {
  chunk_id: number;
  document_id: number;
  document_name: string;
  page_number: number;
  rule_number?: string;
  section_title?: string;
  excerpt: string;
  score: number;
}

export interface Message {
  id: number;
  conversation_id: number;
  sender: 'user' | 'assistant';
  content: string;
  citations: Citation[];
  latency_ms: number;
  created_at: string;
}

export interface Conversation {
  id: number;
  user_id: number;
  title: string;
  created_at: string;
  updated_at: string;
  messages: Message[];
}

export interface DocumentItem {
  id: number;
  title: string;
  filename: string;
  file_size: number;
  mime_type: string;
  total_pages: number;
  status: string;
  is_scanned: boolean;
  chunks_count: number;
  created_at: string;
}

export interface ChunkItem {
  id: number;
  document_id: number;
  chunk_index: number;
  page_number: number;
  rule_number?: string;
  section_title?: string;
  content: string;
  token_count: number;
  score?: number;
}

export interface AnalyticsData {
  total_documents: number;
  total_chunks: number;
  total_conversations: number;
  total_queries: number;
  total_users: number;
  avg_latency_ms: number;
  positive_feedback_count: number;
  negative_feedback_count: number;
  scanned_docs_count: number;
}

function getAuthHeader(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  const token = localStorage.getItem('bccl_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function loginApi(username: string, password: string) {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Authentication failed' }));
    throw new Error(err.detail || 'Login failed');
  }
  return res.json();
}

export async function registerApi(data: { username: string; email: string; password: string; full_name?: string; department?: string }) {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Registration failed' }));
    throw new Error(err.detail || 'Registration failed');
  }
  return res.json();
}

export async function getMeApi(): Promise<User> {
  const res = await fetch(`${API_BASE}/api/auth/me`, {
    headers: getAuthHeader()
  });
  if (!res.ok) throw new Error('Not authenticated');
  return res.json();
}

export async function sendChatMessageApi(message: string, conversation_id?: number, document_id?: number) {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeader()
    },
    body: JSON.stringify({ message, conversation_id, document_id })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to send message' }));
    throw new Error(err.detail || 'Chat query failed');
  }
  return res.json();
}

export async function getConversationsApi(): Promise<Conversation[]> {
  const res = await fetch(`${API_BASE}/api/conversations`, {
    headers: getAuthHeader()
  });
  if (!res.ok) return [];
  return res.json();
}

export async function getConversationApi(id: number): Promise<Conversation> {
  const res = await fetch(`${API_BASE}/api/conversations/${id}`, {
    headers: getAuthHeader()
  });
  if (!res.ok) throw new Error('Conversation not found');
  return res.json();
}

export async function deleteConversationApi(id: number) {
  await fetch(`${API_BASE}/api/conversations/${id}`, {
    method: 'DELETE',
    headers: getAuthHeader()
  });
}

export async function getDocumentsApi(): Promise<DocumentItem[]> {
  const res = await fetch(`${API_BASE}/api/documents`, {
    headers: getAuthHeader()
  });
  if (!res.ok) return [];
  return res.json();
}

export async function getDocumentChunksApi(documentId: number, rule?: string): Promise<ChunkItem[]> {
  const url = new URL(`${API_BASE}/api/documents/${documentId}/chunks`);
  if (rule) url.searchParams.append('rule', rule);
  const res = await fetch(url.toString(), {
    headers: getAuthHeader()
  });
  if (!res.ok) return [];
  return res.json();
}

export async function searchKnowledgeApi(query: string, document_id?: number): Promise<ChunkItem[]> {
  const res = await fetch(`${API_BASE}/api/documents/search`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeader()
    },
    body: JSON.stringify({ query, document_id, top_k: 10 })
  });
  if (!res.ok) return [];
  return res.json();
}

export async function uploadDocumentApi(file: File, title?: string) {
  const formData = new FormData();
  formData.append('file', file);
  if (title) formData.append('title', title);

  const res = await fetch(`${API_BASE}/api/admin/documents/upload`, {
    method: 'POST',
    headers: getAuthHeader(),
    body: formData
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(err.detail || 'Upload failed');
  }
  return res.json();
}

export async function reindexDocumentApi(documentId: number) {
  const res = await fetch(`${API_BASE}/api/admin/documents/${documentId}/reindex`, {
    method: 'POST',
    headers: getAuthHeader()
  });
  if (!res.ok) throw new Error('Reindexing failed');
  return res.json();
}

export async function deleteDocumentApi(documentId: number) {
  const res = await fetch(`${API_BASE}/api/admin/documents/${documentId}`, {
    method: 'DELETE',
    headers: getAuthHeader()
  });
  if (!res.ok) throw new Error('Deletion failed');
}

export async function getAnalyticsApi(): Promise<AnalyticsData> {
  const res = await fetch(`${API_BASE}/api/admin/analytics`, {
    headers: getAuthHeader()
  });
  if (!res.ok) throw new Error('Failed to fetch analytics');
  return res.json();
}

export async function submitFeedbackApi(message_id: number, rating: number, comment?: string) {
  const res = await fetch(`${API_BASE}/api/feedback`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeader()
    },
    body: JSON.stringify({ message_id, rating, comment })
  });
  if (!res.ok) throw new Error('Feedback submission failed');
  return res.json();
}
