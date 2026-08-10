import axios, {
  AxiosError,
  type AxiosInstance,
} from "axios";

import type {
  ApiErrorPayload,
  ChatMessageCreate,
  ChatMessageRead,
  ChatResponse,
  ChatSessionCreate,
  ChatSessionDocumentCreate,
  ChatSessionDocumentRead,
  ChatSessionRead,
  ChatSessionUpdate,
  ChatSourceRead,
  DatabaseHealthResponse,
  DocumentChunkRead,
  DocumentRead,
  HealthResponse,
  UserLoginCreate,
  UserRead,
  UserRegisterCreate,
} from "../types";

const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL?.replace(
    /\/$/,
    "",
  ) ?? "http://localhost:8000";

const API_URL = `${BACKEND_URL}/api`;

const backendClient: AxiosInstance =
  axios.create({
    baseURL: BACKEND_URL,
    timeout: 15_000,
    withCredentials: true,
    headers: {
      Accept: "application/json",
    },
  });

const apiClient: AxiosInstance = axios.create({
  baseURL: API_URL,
  timeout: 120_000,
  withCredentials: true,
  headers: {
    Accept: "application/json",
  },
});

export class ApiRequestError extends Error {
  status: number | null;
  detail: ApiErrorPayload["detail"] | null;

  constructor(
    message: string,
    status: number | null = null,
    detail: ApiErrorPayload["detail"] | null = null,
  ) {
    super(message);

    this.name = "ApiRequestError";
    this.status = status;
    this.detail = detail;
  }
}

function getErrorMessage(
  detail: ApiErrorPayload["detail"] | null,
): string {
  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((issue) => issue.msg)
      .filter(
        (message): message is string =>
          typeof message === "string",
      );

    if (messages.length > 0) {
      return messages.join(" ");
    }
  }

  if (
    detail &&
    !Array.isArray(detail) &&
    typeof detail === "object" &&
    typeof detail.message === "string"
  ) {
    return detail.message;
  }

  return "Backend isteği tamamlanamadı.";
}

function normalizeApiError(
  error: unknown,
): ApiRequestError {
  if (error instanceof ApiRequestError) {
    return error;
  }

  if (axios.isAxiosError<ApiErrorPayload>(error)) {
    const axiosError =
      error as AxiosError<ApiErrorPayload>;

    const status =
      axiosError.response?.status ?? null;

    const detail =
      axiosError.response?.data?.detail ?? null;

    if (axiosError.code === "ECONNABORTED") {
      return new ApiRequestError(
        "Backend isteği zaman aşımına uğradı.",
        status,
        detail,
      );
    }

    if (!axiosError.response) {
      return new ApiRequestError(
        "Backend sunucusuna ulaşılamadı. Backend servisinin çalıştığını kontrol et.",
        null,
        null,
      );
    }

    return new ApiRequestError(
      getErrorMessage(detail),
      status,
      detail,
    );
  }

  if (error instanceof Error) {
    return new ApiRequestError(error.message);
  }

  return new ApiRequestError(
    "Beklenmeyen bir bağlantı hatası oluştu.",
  );
}

async function executeRequest<T>(
  request: () => Promise<T>,
): Promise<T> {
  try {
    return await request();
  } catch (error) {
    throw normalizeApiError(error);
  }
}

export function isAuthenticationError(
  error: unknown,
): boolean {
  return (
    error instanceof ApiRequestError &&
    error.status === 401
  );
}

/* Authentication */

export function getCurrentUser():
  Promise<UserRead> {
  return executeRequest(async () => {
    const response =
      await apiClient.get<UserRead>("/auth/me");

    return response.data;
  });
}

export function registerUser(
  data: UserRegisterCreate,
): Promise<UserRead> {
  return executeRequest(async () => {
    const response =
      await apiClient.post<UserRead>(
        "/auth/register",
        data,
      );

    return response.data;
  });
}

export function loginUser(
  data: UserLoginCreate,
): Promise<UserRead> {
  return executeRequest(async () => {
    const response =
      await apiClient.post<UserRead>(
        "/auth/login",
        data,
      );

    return response.data;
  });
}

export function logoutUser(): Promise<void> {
  return executeRequest(async () => {
    await apiClient.post("/auth/logout");
  });
}

/* Health */

export function getBackendHealth():
  Promise<HealthResponse> {
  return executeRequest(async () => {
    const response =
      await backendClient.get<HealthResponse>(
        "/health",
      );

    return response.data;
  });
}

export function getDatabaseHealth():
  Promise<DatabaseHealthResponse> {
  return executeRequest(async () => {
    const response =
      await backendClient.get<DatabaseHealthResponse>(
        "/health/db",
      );

    return response.data;
  });
}

/* Documents */

export function getDocuments():
  Promise<DocumentRead[]> {
  return executeRequest(async () => {
    const response =
      await apiClient.get<DocumentRead[]>(
        "/documents",
      );

    return response.data;
  });
}

export function getDocument(
  documentId: string,
): Promise<DocumentRead> {
  return executeRequest(async () => {
    const response =
      await apiClient.get<DocumentRead>(
        `/documents/${documentId}`,
      );

    return response.data;
  });
}

export function deleteDocument(
  documentId: string,
): Promise<void> {
  return executeRequest(async () => {
    await apiClient.delete(
      `/documents/${documentId}`,
    );
  });
}

export function getDocumentChunks(
  documentId: string,
): Promise<DocumentChunkRead[]> {
  return executeRequest(async () => {
    const response =
      await apiClient.get<DocumentChunkRead[]>(
        `/documents/${documentId}/chunks`,
      );

    return response.data;
  });
}

export function uploadDocument(
  file: File,
  onProgress?: (percentage: number) => void,
): Promise<DocumentRead> {
  return executeRequest(async () => {
    const formData = new FormData();

    formData.append("file", file);

    const response =
      await apiClient.post<DocumentRead>(
        "/documents",
        formData,
        {
          onUploadProgress: (
            progressEvent,
          ) => {
            if (
              !onProgress ||
              !progressEvent.total
            ) {
              return;
            }

            const percentage = Math.round(
              (progressEvent.loaded * 100) /
                progressEvent.total,
            );

            onProgress(percentage);
          },
        },
      );

    return response.data;
  });
}

/* Chat sessions */

export function getChatSessions():
  Promise<ChatSessionRead[]> {
  return executeRequest(async () => {
    const response =
      await apiClient.get<ChatSessionRead[]>(
        "/chat/sessions",
      );

    return response.data;
  });
}

export function createChatSession(
  data: ChatSessionCreate = {},
): Promise<ChatSessionRead> {
  return executeRequest(async () => {
    const response =
      await apiClient.post<ChatSessionRead>(
        "/chat/sessions",
        data,
      );

    return response.data;
  });
}

export function updateChatSession(
  sessionId: string,
  data: ChatSessionUpdate,
): Promise<ChatSessionRead> {
  return executeRequest(async () => {
    const response =
      await apiClient.patch<ChatSessionRead>(
        `/chat/sessions/${sessionId}`,
        data,
      );

    return response.data;
  });
}

export function deleteChatSession(
  sessionId: string,
): Promise<void> {
  return executeRequest(async () => {
    await apiClient.delete(
      `/chat/sessions/${sessionId}`,
    );
  });
}

export function attachDocumentsToChatSession(
  sessionId: string,
  documentIds: string[],
): Promise<ChatSessionDocumentRead[]> {
  const data: ChatSessionDocumentCreate = {
    document_ids: documentIds,
  };

  return executeRequest(async () => {
    const response =
      await apiClient.post<
        ChatSessionDocumentRead[]
      >(
        `/chat/sessions/${sessionId}/documents`,
        data,
      );

    return response.data;
  });
}

export function getChatSessionDocuments(
  sessionId: string,
): Promise<ChatSessionDocumentRead[]> {
  return executeRequest(async () => {
    const response =
      await apiClient.get<
        ChatSessionDocumentRead[]
      >(
        `/chat/sessions/${sessionId}/documents`,
      );

    return response.data;
  });
}

/* Chat messages */

export function getChatMessages(
  sessionId: string,
): Promise<ChatMessageRead[]> {
  return executeRequest(async () => {
    const response =
      await apiClient.get<ChatMessageRead[]>(
        `/chat/sessions/${sessionId}/messages`,
      );

    return response.data;
  });
}

export function sendChatMessage(
  sessionId: string,
  content: string,
): Promise<ChatResponse> {
  const data: ChatMessageCreate = {
    content,
  };

  return executeRequest(async () => {
    const response =
      await apiClient.post<ChatResponse>(
        `/chat/sessions/${sessionId}/messages`,
        data,
      );

    return response.data;
  });
}

export function getChatMessageSources(
  sessionId: string,
  messageId: string,
): Promise<ChatSourceRead[]> {
  return executeRequest(async () => {
    const response =
      await apiClient.get<ChatSourceRead[]>(
        `/chat/sessions/${sessionId}/messages/${messageId}/sources`,
      );

    return response.data;
  });
}

export { API_URL, BACKEND_URL };