import { beforeEach, describe, expect, it, vi } from "vitest";


const axiosMocks = vi.hoisted(() => {
  const backendClient = {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  };
  const apiClient = {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  };
  const create = vi.fn(
    (config: { baseURL: string }) => (
      config.baseURL.endsWith("/api")
        ? apiClient
        : backendClient
    ),
  );
  const isAxiosError = vi.fn(
    (error: unknown) => (
      typeof error === "object"
      && error !== null
      && "isAxiosError" in error
      && error.isAxiosError === true
    ),
  );

  return {
    apiClient,
    backendClient,
    create,
    isAxiosError,
  };
});


vi.mock("axios", () => ({
  default: {
    create: axiosMocks.create,
    isAxiosError: axiosMocks.isAxiosError,
  },
  AxiosError: class AxiosError extends Error {},
}));


import {
  API_URL,
  BACKEND_URL,
  ApiRequestError,
  attachDocumentsToChatSession,
  createChatSession,
  deleteChatSession,
  deleteDocument,
  getBackendHealth,
  getChatMessageSources,
  getChatMessages,
  getChatSessionDocuments,
  getChatSessions,
  getCurrentUser,
  getDatabaseHealth,
  getDocument,
  getDocumentChunks,
  getDocuments,
  isAuthenticationError,
  loginUser,
  logoutUser,
  registerUser,
  sendChatMessage,
  updateChatSession,
  uploadDocument,
} from "./api";


function resetClientMocks(): void {
  for (const client of [
    axiosMocks.backendClient,
    axiosMocks.apiClient,
  ]) {
    client.get.mockReset();
    client.post.mockReset();
    client.patch.mockReset();
    client.delete.mockReset();
  }
}


function makeAxiosError(
  options: {
    status?: number;
    detail?: unknown;
    code?: string;
    includeResponse?: boolean;
  } = {},
): object {
  const includeResponse =
    options.includeResponse ?? true;

  return {
    isAxiosError: true,
    code: options.code,
    response: includeResponse
      ? {
          status: options.status ?? 500,
          data: { detail: options.detail },
        }
      : undefined,
  };
}


beforeEach(() => {
  resetClientMocks();
  axiosMocks.isAxiosError.mockClear();
});


describe("API istemci ayarları", () => {
  it("yerel backend adresini ve güvenli çerezli istemcileri kullanır", () => {
    expect(BACKEND_URL).toBe("http://localhost:8000");
    expect(API_URL).toBe("http://localhost:8000/api");
    expect(axiosMocks.create).toHaveBeenCalledWith(
      expect.objectContaining({
        baseURL: BACKEND_URL,
        timeout: 15_000,
        withCredentials: true,
      }),
    );
    expect(axiosMocks.create).toHaveBeenCalledWith(
      expect.objectContaining({
        baseURL: API_URL,
        timeout: 120_000,
        withCredentials: true,
      }),
    );
  });

  it("ApiRequestError alanlarını korur", () => {
    const detail = { message: "Ayrıntı" };
    const error = new ApiRequestError(
      "İstek başarısız",
      422,
      detail,
    );

    expect(error).toBeInstanceOf(Error);
    expect(error.name).toBe("ApiRequestError");
    expect(error.message).toBe("İstek başarısız");
    expect(error.status).toBe(422);
    expect(error.detail).toEqual(detail);
  });
});


describe("kimlik doğrulama ve sağlık istekleri", () => {
  it("kullanıcı isteklerini doğru endpoint ve payload ile gönderir", async () => {
    const user = {
      id: "user-1",
    } as Awaited<ReturnType<typeof getCurrentUser>>;
    const loginPayload = {
      email: "user@example.com",
      password: "secret-password",
    } as Parameters<typeof loginUser>[0];
    const registerPayload = {
      email: "user@example.com",
      password: "secret-password",
      full_name: "Test Kullanıcısı",
    } as Parameters<typeof registerUser>[0];

    axiosMocks.apiClient.get.mockResolvedValueOnce({ data: user });
    axiosMocks.apiClient.post
      .mockResolvedValueOnce({ data: user })
      .mockResolvedValueOnce({ data: user })
      .mockResolvedValueOnce({ data: undefined });

    await expect(getCurrentUser()).resolves.toBe(user);
    await expect(registerUser(registerPayload)).resolves.toBe(user);
    await expect(loginUser(loginPayload)).resolves.toBe(user);
    await expect(logoutUser()).resolves.toBeUndefined();

    expect(axiosMocks.apiClient.get).toHaveBeenCalledWith("/auth/me");
    expect(axiosMocks.apiClient.post).toHaveBeenNthCalledWith(
      1,
      "/auth/register",
      registerPayload,
    );
    expect(axiosMocks.apiClient.post).toHaveBeenNthCalledWith(
      2,
      "/auth/login",
      loginPayload,
    );
    expect(axiosMocks.apiClient.post).toHaveBeenNthCalledWith(
      3,
      "/auth/logout",
    );
  });

  it("uygulama ve veritabanı sağlık endpointlerini ayırır", async () => {
    const health = { status: "ok" } as Awaited<
      ReturnType<typeof getBackendHealth>
    >;
    const database = { database: "connected" } as Awaited<
      ReturnType<typeof getDatabaseHealth>
    >;

    axiosMocks.backendClient.get
      .mockResolvedValueOnce({ data: health })
      .mockResolvedValueOnce({ data: database });

    await expect(getBackendHealth()).resolves.toBe(health);
    await expect(getDatabaseHealth()).resolves.toBe(database);

    expect(axiosMocks.backendClient.get).toHaveBeenNthCalledWith(
      1,
      "/health",
    );
    expect(axiosMocks.backendClient.get).toHaveBeenNthCalledWith(
      2,
      "/health/db",
    );
  });
});


describe("doküman istekleri", () => {
  it("listeleme, ayrıntı, parça ve silme endpointlerini kullanır", async () => {
    const documents = [] as Awaited<ReturnType<typeof getDocuments>>;
    const document = { id: "doc-1" } as Awaited<
      ReturnType<typeof getDocument>
    >;
    const chunks = [] as Awaited<ReturnType<typeof getDocumentChunks>>;

    axiosMocks.apiClient.get
      .mockResolvedValueOnce({ data: documents })
      .mockResolvedValueOnce({ data: document })
      .mockResolvedValueOnce({ data: chunks });
    axiosMocks.apiClient.delete.mockResolvedValueOnce({ data: undefined });

    await expect(getDocuments()).resolves.toBe(documents);
    await expect(getDocument("doc-1")).resolves.toBe(document);
    await expect(getDocumentChunks("doc-1")).resolves.toBe(chunks);
    await expect(deleteDocument("doc-1")).resolves.toBeUndefined();

    expect(axiosMocks.apiClient.get).toHaveBeenNthCalledWith(
      1,
      "/documents",
    );
    expect(axiosMocks.apiClient.get).toHaveBeenNthCalledWith(
      2,
      "/documents/doc-1",
    );
    expect(axiosMocks.apiClient.get).toHaveBeenNthCalledWith(
      3,
      "/documents/doc-1/chunks",
    );
    expect(axiosMocks.apiClient.delete).toHaveBeenCalledWith(
      "/documents/doc-1",
    );
  });

  it("yükleme ilerlemesini yüzdeye dönüştürür", async () => {
    const document = { id: "doc-1" } as Awaited<
      ReturnType<typeof uploadDocument>
    >;
    const progress = vi.fn();
    const file = new File(
      ["test content"],
      "test.txt",
      { type: "text/plain" },
    );

    axiosMocks.apiClient.post.mockImplementationOnce(
      async (
        endpoint: string,
        body: FormData,
        config: {
          onUploadProgress: (
            event: { loaded: number; total?: number },
          ) => void;
        },
      ) => {
        expect(endpoint).toBe("/documents");
        expect(body.get("file")).toBe(file);
        config.onUploadProgress({ loaded: 3, total: 4 });
        config.onUploadProgress({ loaded: 3 });

        return { data: document };
      },
    );

    await expect(uploadDocument(file, progress)).resolves.toBe(document);
    expect(progress).toHaveBeenCalledOnce();
    expect(progress).toHaveBeenCalledWith(75);
  });
});


describe("sohbet istekleri", () => {
  it("oturum CRUD ve belge bağlama isteklerini gönderir", async () => {
    const sessions = [] as Awaited<ReturnType<typeof getChatSessions>>;
    const session = { id: "session-1" } as Awaited<
      ReturnType<typeof createChatSession>
    >;
    const linkedDocuments = [] as Awaited<
      ReturnType<typeof attachDocumentsToChatSession>
    >;
    const updatePayload = {
      title: "Yeni başlık",
    } as Parameters<typeof updateChatSession>[1];

    axiosMocks.apiClient.get
      .mockResolvedValueOnce({ data: sessions })
      .mockResolvedValueOnce({ data: linkedDocuments });
    axiosMocks.apiClient.post
      .mockResolvedValueOnce({ data: session })
      .mockResolvedValueOnce({ data: linkedDocuments });
    axiosMocks.apiClient.patch.mockResolvedValueOnce({ data: session });
    axiosMocks.apiClient.delete.mockResolvedValueOnce({ data: undefined });

    await expect(getChatSessions()).resolves.toBe(sessions);
    await expect(createChatSession()).resolves.toBe(session);
    await expect(updateChatSession("session-1", updatePayload)).resolves.toBe(session);
    await expect(deleteChatSession("session-1")).resolves.toBeUndefined();
    await expect(
      attachDocumentsToChatSession("session-1", ["doc-1"]),
    ).resolves.toBe(linkedDocuments);
    await expect(
      getChatSessionDocuments("session-1"),
    ).resolves.toBe(linkedDocuments);

    expect(axiosMocks.apiClient.post).toHaveBeenNthCalledWith(
      1,
      "/chat/sessions",
      {},
    );
    expect(axiosMocks.apiClient.patch).toHaveBeenCalledWith(
      "/chat/sessions/session-1",
      updatePayload,
    );
    expect(axiosMocks.apiClient.delete).toHaveBeenCalledWith(
      "/chat/sessions/session-1",
    );
    expect(axiosMocks.apiClient.post).toHaveBeenNthCalledWith(
      2,
      "/chat/sessions/session-1/documents",
      { document_ids: ["doc-1"] },
    );
    expect(axiosMocks.apiClient.get).toHaveBeenNthCalledWith(
      2,
      "/chat/sessions/session-1/documents",
    );
  });

  it("mesaj ve kaynak endpointlerini kullanır", async () => {
    const messages = [] as Awaited<ReturnType<typeof getChatMessages>>;
    const response = {
      user_message: {},
      assistant_message: {},
      sources: [],
    } as unknown as Awaited<
      ReturnType<typeof sendChatMessage>
    >;
    const sources = [] as Awaited<ReturnType<typeof getChatMessageSources>>;

    axiosMocks.apiClient.get
      .mockResolvedValueOnce({ data: messages })
      .mockResolvedValueOnce({ data: sources });
    axiosMocks.apiClient.post.mockResolvedValueOnce({ data: response });

    await expect(getChatMessages("session-1")).resolves.toBe(messages);
    await expect(
      sendChatMessage("session-1", "Belge ne anlatıyor?"),
    ).resolves.toBe(response);
    await expect(
      getChatMessageSources("session-1", "message-1"),
    ).resolves.toBe(sources);

    expect(axiosMocks.apiClient.get).toHaveBeenNthCalledWith(
      1,
      "/chat/sessions/session-1/messages",
    );
    expect(axiosMocks.apiClient.post).toHaveBeenCalledWith(
      "/chat/sessions/session-1/messages",
      { content: "Belge ne anlatıyor?" },
    );
    expect(axiosMocks.apiClient.get).toHaveBeenNthCalledWith(
      2,
      "/chat/sessions/session-1/messages/message-1/sources",
    );
  });
});


describe("API hata normalleştirme", () => {
  it("zaman aşımını açıklayıcı hataya dönüştürür", async () => {
    axiosMocks.apiClient.get.mockRejectedValueOnce(
      makeAxiosError({
        code: "ECONNABORTED",
        includeResponse: false,
      }),
    );

    await expect(getDocuments()).rejects.toMatchObject({
      name: "ApiRequestError",
      message: "Backend isteği zaman aşımına uğradı.",
      status: null,
    });
  });

  it("ağ hatasını kullanıcıya açıklar", async () => {
    axiosMocks.apiClient.get.mockRejectedValueOnce(
      makeAxiosError({ includeResponse: false }),
    );

    await expect(getDocuments()).rejects.toMatchObject({
      message: (
        "Backend sunucusuna ulaşılamadı. "
        + "Backend servisinin çalıştığını kontrol et."
      ),
      status: null,
      detail: null,
    });
  });

  it.each([
    ["Metin ayrıntısı", "Metin ayrıntısı"],
    [[{ msg: "Birinci" }, { msg: "İkinci" }], "Birinci İkinci"],
    [{ message: "Nesne ayrıntısı" }, "Nesne ayrıntısı"],
    [null, "Backend isteği tamamlanamadı."],
  ])(
    "backend ayrıntısını hata mesajına dönüştürür",
    async (detail, expectedMessage) => {
      axiosMocks.apiClient.get.mockRejectedValueOnce(
        makeAxiosError({ status: 422, detail }),
      );

      await expect(getDocuments()).rejects.toMatchObject({
        message: expectedMessage,
        status: 422,
        detail,
      });
    },
  );

  it("yerel Error ve bilinmeyen değerleri korumalı biçimde sarar", async () => {
    axiosMocks.apiClient.get
      .mockRejectedValueOnce(new Error("Yerel hata"))
      .mockRejectedValueOnce(42);

    await expect(getDocuments()).rejects.toMatchObject({
      message: "Yerel hata",
      status: null,
    });
    await expect(getDocuments()).rejects.toMatchObject({
      message: "Beklenmeyen bir bağlantı hatası oluştu.",
      status: null,
    });
  });

  it("401 ApiRequestError değerini kimlik doğrulama hatası olarak tanır", () => {
    expect(
      isAuthenticationError(
        new ApiRequestError("Oturum gerekli", 401),
      ),
    ).toBe(true);
    expect(
      isAuthenticationError(
        new ApiRequestError("Yetki yok", 403),
      ),
    ).toBe(false);
    expect(isAuthenticationError(new Error("Hata"))).toBe(false);
  });
});
