/**
 * api.ts — typed fetch wrappers for all REST endpoints.
 *
 * Base URL is read from the VITE_API_BASE_URL environment variable.
 * Falls back to '' (same origin) so the Vite proxy can forward /api/* in dev.
 *
 * All functions throw on non-2xx responses with a descriptive error message.
 */

const BASE = import.meta.env.VITE_API_BASE_URL ?? ''

// ---------------------------------------------------------------------------
// Types (mirrors backend Pydantic schemas)
// ---------------------------------------------------------------------------

export interface Document {
  id: number
  user_id: number
  title: string
  filename: string
  file_type: string
  source_lang: string | null
  status: 'uploaded' | 'extracting' | 'ready' | 'failed'
  created_at: string
}

export interface Chapter {
  id: number
  document_id: number
  index: number
  title: string
  text_path: string | null
  lang: string
  status: 'pending' | 'processing' | 'ready' | 'failed'
}

export interface PlaybackState {
  id: number
  user_id: number
  document_id: number
  chapter_index: number
  position_s: number
  speed: number
  audio_lang: string
  updated_at: string
}

export interface Job {
  id: number
  document_id: number
  stage: string
  progress: number
  error: string | null
  created_at: string
  updated_at: string
}

export interface HealthResponse {
  status: string
  version: string
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${BASE}${path}`
  const response = await fetch(url, options)

  if (!response.ok) {
    let detail = `HTTP ${response.status}`
    try {
      const json = await response.json()
      detail = json.detail ?? JSON.stringify(json)
    } catch { /* ignore */ }
    throw new Error(`${detail} — ${path}`)
  }

  if (response.status === 204) return undefined as unknown as T
  return response.json()
}

// ---------------------------------------------------------------------------
// API client
// ---------------------------------------------------------------------------

export const api = {
  /** System */
  health: () => request<HealthResponse>('/health'),

  /** Documents */
  listDocuments: () => request<Document[]>('/documents/'),

  getDocument: (id: number) => request<Document>(`/documents/${id}`),

  uploadDocument: async (file: File, title?: string): Promise<Document> => {
    const form = new FormData()
    form.append('file', file)
    if (title) form.append('title', title)
    return request<Document>('/documents/', { method: 'POST', body: form })
  },

  deleteDocument: (id: number) =>
    request<void>(`/documents/${id}`, { method: 'DELETE' }),

  listChapters: (docId: number) =>
    request<Chapter[]>(`/documents/${docId}/chapters`),

  /** Chapters */
  regenerateChapter: (chapterId: number) =>
    request<Chapter>(`/chapters/${chapterId}/regenerate`, { method: 'POST' }),

  /** Audio */
  getChapterAudioUrl: (chapterId: number) => `${BASE}/chapters/${chapterId}/audio`,

  /** Playback state */
  getPlaybackState: (docId: number) =>
    request<PlaybackState>(`/playback/${docId}`),

  updatePlaybackState: (
    docId: number,
    payload: Partial<Omit<PlaybackState, 'id' | 'user_id' | 'document_id' | 'updated_at'>>,
  ) =>
    request<PlaybackState>(`/playback/${docId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
}
