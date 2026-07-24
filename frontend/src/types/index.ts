export type DocumentStatus =
  | "processing"
  | "ready"
  | "failed"
  | string;

export type ChatRole =
  | "user"
  | "assistant"
  | "system"
  | string;

export interface DocumentRead {
  id: string;
  user_id: string;
  original_filename: string;
  stored_filename: string;
  file_type: string;
  mime_type: string | null;
  file_size: number | null;
  storage_path: string;
  status: DocumentStatus;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentChunkRead {
  id: string;
  document_id: string;
  chunk_index: number;
  content: string;
  source_metadata: Record<string, unknown> | null;
  created_at?: string;
}

export interface ChatSessionCreate {
  title?: string | null;
}

export interface ChatSessionUpdate {
  title: string;
}

export interface ChatSessionRead {
  id: string;
  user_id: string;
  title: string | null;
  created_at: string;
}

export interface ChatMessageCreate {
  content: string;
}

export interface ChatMessageRead {
  id: string;
  session_id: string;
  role: ChatRole;
  content: string;
  created_at: string;
}

export interface ChatSourceRead {
  chunk_id: string;
  document_id: string;
  chunk_index: number;
  content: string;
  similarity_score: number;
  original_filename: string | null;
}

export interface ChatResponse {
  user_message: ChatMessageRead;
  assistant_message: ChatMessageRead;
  sources: ChatSourceRead[];
}

export interface ChatSessionDocumentCreate {
  document_ids: string[];
}

export interface ChatSessionDocumentRead {
  id: string;
  session_id: string;
  document_id: string;
  created_at: string;
}

export interface HealthResponse {
  status: string;
}

export interface DatabaseHealthResponse {
  database: "connected" | "error";
  detail?: string;
}

export interface ApiErrorPayload {
  detail?:
    | string
    | {
        message?: string;
        document_ids?: string[];
        [key: string]: unknown;
      };
}