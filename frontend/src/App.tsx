import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import "./App.css";

import AppHeader from "./components/AppHeader";
import AuthScreen from "./components/AuthScreen";
import ChatWorkspace from "./components/ChatWorkspace";
import SourceInspector from "./components/SourceInspector";
import SourceSidebar from "./components/SourceSidebar";
import UploadModal from "./components/UploadModal";
import WorkspaceDialog, {
  type WorkspaceDialogState,
} from "./components/WorkspaceDialog";

import {
  attachDocumentsToChatSession,
  createChatSession,
  deleteChatSession,
  deleteDocument,
  getChatMessages,
  getChatMessageSources,
  getChatSessionDocuments,
  getChatSessions,
  getCurrentUser,
  getDocuments,
  isAuthenticationError,
  loginUser,
  logoutUser,
  registerUser,
  sendChatMessage,
  updateChatSession,
  uploadDocument,
} from "./services/api";

import type {
  ChatMessageRead,
  ChatSessionRead,
  ChatSourceRead,
  DocumentRead,
  UserLoginCreate,
  UserRead,
  UserRegisterCreate,
} from "./types";

type Theme = "light" | "dark";

function getInitialTheme(): Theme {
  const storedTheme = localStorage.getItem(
    "smart-rag-theme",
  );

  if (
    storedTheme === "light" ||
    storedTheme === "dark"
  ) {
    return storedTheme;
  }

  return window.matchMedia(
    "(prefers-color-scheme: dark)",
  ).matches
    ? "dark"
    : "light";
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return "Beklenmeyen bir hata oluştu.";
}

function App() {
  const [theme, setTheme] =
    useState<Theme>(getInitialTheme);

  const [currentUser, setCurrentUser] =
    useState<UserRead | null>(null);

  const [authChecking, setAuthChecking] =
    useState(true);

  const [authSubmitting, setAuthSubmitting] =
    useState(false);

  const [loggingOut, setLoggingOut] =
    useState(false);

  const [authError, setAuthError] =
    useState<string | null>(null);

  const [sourcePanelOpen, setSourcePanelOpen] =
    useState(true);

  const [uploadModalOpen, setUploadModalOpen] =
    useState(false);

  const [workspaceDialog, setWorkspaceDialog] =
    useState<WorkspaceDialogState | null>(null);

  const [documents, setDocuments] =
    useState<DocumentRead[]>([]);

  const [sessions, setSessions] =
    useState<ChatSessionRead[]>([]);

  const [messages, setMessages] =
    useState<ChatMessageRead[]>([]);

  const [sources, setSources] =
    useState<ChatSourceRead[]>([]);

  const [
    selectedSourceMessageId,
    setSelectedSourceMessageId,
  ] = useState<string | null>(null);

  const [sourcesLoading, setSourcesLoading] =
    useState(false);

  const sourceRequestIdRef = useRef(0);

  const [
    selectedDocumentIds,
    setSelectedDocumentIds,
  ] = useState<string[]>([]);

  const [activeSessionId, setActiveSessionId] =
    useState<string | null>(null);

  const [initialLoading, setInitialLoading] =
    useState(true);

  const [messagesLoading, setMessagesLoading] =
    useState(false);

  const [creatingSession, setCreatingSession] =
    useState(false);

  const [sendingMessage, setSendingMessage] =
    useState(false);

  const [
    deletingDocumentId,
    setDeletingDocumentId,
  ] = useState<string | null>(null);

  const [
    deletingSessionId,
    setDeletingSessionId,
  ] = useState<string | null>(null);

  const [
    renamingSessionId,
    setRenamingSessionId,
  ] = useState<string | null>(null);

  const [sidebarError, setSidebarError] =
    useState<string | null>(null);

  const [chatError, setChatError] =
    useState<string | null>(null);

  const dark = theme === "dark";

  const workspaceDialogBusy =
    deletingDocumentId !== null ||
    deletingSessionId !== null ||
    renamingSessionId !== null;

  const resetWorkspace = useCallback(() => {
    setDocuments([]);
    setSessions([]);
    setMessages([]);
    setSources([]);
    setSelectedSourceMessageId(null);
    setSourcesLoading(false);
    setSelectedDocumentIds([]);
    setActiveSessionId(null);

    sourceRequestIdRef.current += 1;

    setUploadModalOpen(false);
    setWorkspaceDialog(null);
    setInitialLoading(true);
    setMessagesLoading(false);
    setCreatingSession(false);
    setSendingMessage(false);
    setDeletingDocumentId(null);
    setDeletingSessionId(null);
    setRenamingSessionId(null);

    setSidebarError(null);
    setChatError(null);
  }, []);

  const handleAuthenticationFailure =
    useCallback(
      (error: unknown): boolean => {
        if (!isAuthenticationError(error)) {
          return false;
        }

        resetWorkspace();
        setCurrentUser(null);
        setAuthError(
          "Oturumunuz sona erdi. Lütfen tekrar giriş yapın.",
        );

        return true;
      },
      [resetWorkspace],
    );

  useEffect(() => {
    document.documentElement.dataset.theme =
      theme;

    localStorage.setItem(
      "smart-rag-theme",
      theme,
    );
  }, [theme]);

  useEffect(() => {
    let active = true;

    async function checkAuthentication() {
      setAuthChecking(true);
      setAuthError(null);

      try {
        const user = await getCurrentUser();

        if (active) {
          setCurrentUser(user);
        }
      } catch (error) {
        if (!active) {
          return;
        }

        setCurrentUser(null);

        if (!isAuthenticationError(error)) {
          setAuthError(
            getErrorMessage(error),
          );
        }
      } finally {
        if (active) {
          setAuthChecking(false);
        }
      }
    }

    void checkAuthentication();

    return () => {
      active = false;
    };
  }, []);

  const loadDocuments = useCallback(async () => {
    const loadedDocuments =
      await getDocuments();

    setDocuments(loadedDocuments);

    setSelectedDocumentIds(
      (currentIds) => {
        const availableIds = new Set(
          loadedDocuments
            .filter(
              (document) =>
                document.status === "ready",
            )
            .map(
              (document) =>
                document.id,
            ),
        );

        return currentIds.filter((id) =>
          availableIds.has(id),
        );
      },
    );

    return loadedDocuments;
  }, []);

  const loadSessions = useCallback(async () => {
    const loadedSessions =
      await getChatSessions();

    setSessions(loadedSessions);

    return loadedSessions;
  }, []);

  useEffect(() => {
    if (!currentUser) {
      return;
    }

    let active = true;

    async function initializeApplication() {
      setInitialLoading(true);
      setSidebarError(null);

      try {
        const [
          loadedDocuments,
          loadedSessions,
        ] = await Promise.all([
          loadDocuments(),
          loadSessions(),
        ]);

        if (!active) {
          return;
        }

        if (loadedSessions.length > 0) {
          setActiveSessionId(
            loadedSessions[0].id,
          );

          return;
        }

        const firstReadyDocument =
          loadedDocuments.find(
            (document) =>
              document.status === "ready",
          );

        if (firstReadyDocument) {
          setSelectedDocumentIds([
            firstReadyDocument.id,
          ]);
        }
      } catch (error) {
        if (!active) {
          return;
        }

        if (
          !handleAuthenticationFailure(error)
        ) {
          setSidebarError(
            getErrorMessage(error),
          );
        }
      } finally {
        if (active) {
          setInitialLoading(false);
        }
      }
    }

    void initializeApplication();

    return () => {
      active = false;
    };
  }, [
    currentUser,
    handleAuthenticationFailure,
    loadDocuments,
    loadSessions,
  ]);

  useEffect(() => {
    sourceRequestIdRef.current += 1;

    const sourceRequestId =
      sourceRequestIdRef.current;

    setSources([]);
    setSelectedSourceMessageId(null);
    setSourcesLoading(false);

    if (!currentUser) {
      setMessages([]);
      setSelectedDocumentIds([]);
      return;
    }

    if (!activeSessionId) {
      setMessages([]);
      return;
    }

    setMessages([]);
    setSelectedDocumentIds([]);

    const sessionId = activeSessionId;
    let active = true;

    async function loadSessionWorkspace() {
      setMessagesLoading(true);
      setChatError(null);

      try {
        const [
          loadedMessages,
          linkedDocuments,
        ] = await Promise.all([
          getChatMessages(sessionId),
          getChatSessionDocuments(
            sessionId,
          ),
        ]);

        if (!active) {
          return;
        }

        setMessages(loadedMessages);

        setSelectedDocumentIds(
          linkedDocuments.map(
            (link) => link.document_id,
          ),
        );

        const lastAssistantMessage =
          [...loadedMessages]
            .reverse()
            .find(
              (message) =>
                message.role ===
                "assistant",
            );

        if (!lastAssistantMessage) {
          setSources([]);
          return;
        }

        setSelectedSourceMessageId(
          lastAssistantMessage.id,
        );
        setSourcesLoading(true);

        try {
          const loadedSources =
            await getChatMessageSources(
              sessionId,
              lastAssistantMessage.id,
            );

          if (
            active &&
            sourceRequestIdRef.current ===
              sourceRequestId
          ) {
            setSources(loadedSources);
          }
        } catch (error) {
          if (
            !active ||
            sourceRequestIdRef.current !==
              sourceRequestId
          ) {
            return;
          }

          if (
            !handleAuthenticationFailure(
              error,
            )
          ) {
            setSources([]);
            setChatError(
              "Sohbet yüklendi ancak eski kaynaklar alınamadı.",
            );
          }
        } finally {
          if (
            active &&
            sourceRequestIdRef.current ===
              sourceRequestId
          ) {
            setSourcesLoading(false);
          }
        }
      } catch (error) {
        if (!active) {
          return;
        }

        if (
          !handleAuthenticationFailure(error)
        ) {
          setChatError(
            getErrorMessage(error),
          );
        }
      } finally {
        if (active) {
          setMessagesLoading(false);
        }
      }
    }

    void loadSessionWorkspace();

    return () => {
      active = false;
    };
  }, [
    activeSessionId,
    currentUser,
    handleAuthenticationFailure,
  ]);

  async function handleLogin(
    credentials: UserLoginCreate,
  ): Promise<void> {
    if (authSubmitting) {
      return;
    }

    setAuthSubmitting(true);
    setAuthError(null);

    try {
      const user =
        await loginUser(credentials);

      resetWorkspace();
      setCurrentUser(user);
    } catch (error) {
      setAuthError(
        getErrorMessage(error),
      );
    } finally {
      setAuthSubmitting(false);
    }
  }

  async function handleRegister(
    registration: UserRegisterCreate,
  ): Promise<void> {
    if (authSubmitting) {
      return;
    }

    setAuthSubmitting(true);
    setAuthError(null);

    try {
      const user =
        await registerUser(registration);

      resetWorkspace();
      setCurrentUser(user);
    } catch (error) {
      setAuthError(
        getErrorMessage(error),
      );
    } finally {
      setAuthSubmitting(false);
    }
  }

  async function handleLogout():
    Promise<void> {
    if (loggingOut) {
      return;
    }

    setLoggingOut(true);

    try {
      await logoutUser();
    } catch {
      // Sunucuya ulaşılamasa bile yerel
      // kullanıcı oturumu kapatılır.
    } finally {
      resetWorkspace();
      setCurrentUser(null);
      setAuthError(null);
      setLoggingOut(false);
    }
  }

  function toggleTheme() {
    setTheme((currentTheme) =>
      currentTheme === "dark"
        ? "light"
        : "dark",
    );
  }

  function toggleDocument(
    documentId: string,
  ) {
    setSelectedDocumentIds((currentIds) => {
      if (currentIds.includes(documentId)) {
        return currentIds.filter(
          (id) => id !== documentId,
        );
      }

      return [
        ...currentIds,
        documentId,
      ];
    });
  }

  async function handleDeleteDocument(
    documentId: string,
  ): Promise<void> {
    if (deletingDocumentId) {
      return;
    }

    const documentToDelete =
      documents.find(
        (document) =>
          document.id === documentId,
      );

    if (!documentToDelete) {
      return;
    }

    setSidebarError(null);
    setWorkspaceDialog({
      type: "delete-document",
      targetId: documentId,
      targetName:
        documentToDelete.original_filename,
    });
  }

  async function handleDeleteSession(
    sessionId: string,
  ): Promise<void> {
    if (deletingSessionId) {
      return;
    }

    const sessionToDelete =
      sessions.find(
        (session) =>
          session.id === sessionId,
      );

    if (!sessionToDelete) {
      return;
    }

    const sessionTitle =
      sessionToDelete.title ||
      "Başlıksız sohbet";

    setSidebarError(null);
    setWorkspaceDialog({
      type: "delete-session",
      targetId: sessionId,
      targetName: sessionTitle,
    });
  }

  async function handleRenameSession(
    sessionId: string,
  ): Promise<void> {
    if (renamingSessionId) {
      return;
    }

    const sessionToRename =
      sessions.find(
        (session) =>
          session.id === sessionId,
      );

    if (!sessionToRename) {
      return;
    }

    const currentTitle =
      sessionToRename.title ||
      "Başlıksız sohbet";

    setSidebarError(null);
    setWorkspaceDialog({
      type: "rename-session",
      targetId: sessionId,
      targetName: currentTitle,
    });
  }

  async function confirmWorkspaceDialog(
    value: string,
  ): Promise<boolean> {
    if (!workspaceDialog) {
      return false;
    }

    const { type, targetId, targetName } =
      workspaceDialog;

    setSidebarError(null);

    if (type === "delete-document") {
      setDeletingDocumentId(targetId);

      try {
        await deleteDocument(targetId);

        setDocuments((currentDocuments) =>
          currentDocuments.filter(
            (document) =>
              document.id !== targetId,
          ),
        );

        setSelectedDocumentIds((currentIds) =>
          currentIds.filter(
            (id) => id !== targetId,
          ),
        );

        setSources((currentSources) =>
          currentSources.filter(
            (source) =>
              source.document_id !== targetId,
          ),
        );

        return true;
      } catch (error) {
        if (!handleAuthenticationFailure(error)) {
          setSidebarError(getErrorMessage(error));
        }

        return false;
      } finally {
        setDeletingDocumentId(null);
      }
    }

    if (type === "delete-session") {
      setDeletingSessionId(targetId);

      try {
        await deleteChatSession(targetId);

        const remainingSessions =
          sessions.filter(
            (session) => session.id !== targetId,
          );

        setSessions(remainingSessions);

        if (activeSessionId === targetId) {
          const nextSession =
            remainingSessions[0] ?? null;

          sourceRequestIdRef.current += 1;
          setSelectedSourceMessageId(null);
          setSourcesLoading(false);
          setActiveSessionId(
            nextSession?.id ?? null,
          );
          setMessages([]);
          setSources([]);
        }

        return true;
      } catch (error) {
        if (!handleAuthenticationFailure(error)) {
          setSidebarError(getErrorMessage(error));
        }

        return false;
      } finally {
        setDeletingSessionId(null);
      }
    }

    const normalizedTitle = value.trim();

    if (!normalizedTitle) {
      setSidebarError(
        "Sohbet adı boş bırakılamaz.",
      );
      return false;
    }

    if (normalizedTitle === targetName) {
      return true;
    }

    setRenamingSessionId(targetId);

    try {
      const updatedSession =
        await updateChatSession(targetId, {
          title: normalizedTitle,
        });

      setSessions((currentSessions) =>
        currentSessions.map((session) =>
          session.id === targetId
            ? updatedSession
            : session,
        ),
      );

      return true;
    } catch (error) {
      if (!handleAuthenticationFailure(error)) {
        setSidebarError(getErrorMessage(error));
      }

      return false;
    } finally {
      setRenamingSessionId(null);
    }
  }

  async function handleCreateSession():
    Promise<ChatSessionRead | null> {
    if (creatingSession) {
      return null;
    }

    setCreatingSession(true);
    setSidebarError(null);
    setChatError(null);

    try {
      const session =
        await createChatSession({
          title: "Yeni sohbet",
        });

      setSessions(
        (currentSessions) => [
          session,
          ...currentSessions.filter(
            (currentSession) =>
              currentSession.id !==
              session.id,
          ),
        ],
      );

      setActiveSessionId(session.id);
      setMessages([]);
      setSources([]);
      setSelectedSourceMessageId(null);
      setSourcesLoading(false);

      sourceRequestIdRef.current += 1;

      return session;
    } catch (error) {
      if (
        !handleAuthenticationFailure(error)
      ) {
        setSidebarError(
          getErrorMessage(error),
        );
      }

      return null;
    } finally {
      setCreatingSession(false);
    }
  }

  async function handleUpload(
    files: File[],
  ): Promise<void> {
    setSidebarError(null);

    try {
      const uploadedDocuments:
        DocumentRead[] = [];

      for (const file of files) {
        const uploadedDocument =
          await uploadDocument(file);

        uploadedDocuments.push(
          uploadedDocument,
        );
      }

      await loadDocuments();

      const readyUploadedIds =
        uploadedDocuments
          .filter(
            (document) =>
              document.status === "ready",
          )
          .map(
            (document) =>
              document.id,
          );

      if (
        readyUploadedIds.length > 0
      ) {
        setSelectedDocumentIds(
          (currentIds) => [
            ...new Set([
              ...currentIds,
              ...readyUploadedIds,
            ]),
          ],
        );
      }

      const failedDocuments =
        uploadedDocuments.filter(
          (document) =>
            document.status === "failed",
        );

      if (
        failedDocuments.length > 0
      ) {
        const failedNames =
          failedDocuments
            .map(
              (document) =>
                document.original_filename,
            )
            .join(", ");

        throw new Error(
          `Bazı belgeler işlenemedi: ${failedNames}`,
        );
      }
    } catch (error) {
      if (
        !handleAuthenticationFailure(error)
      ) {
        setSidebarError(
          getErrorMessage(error),
        );
      }

      throw error;
    }
  }

  async function handleAssistantMessageSelect(
    messageId: string,
  ): Promise<void> {
    if (!activeSessionId) {
      return;
    }

    const sessionId = activeSessionId;
    const requestId =
      sourceRequestIdRef.current + 1;

    sourceRequestIdRef.current = requestId;

    setSelectedSourceMessageId(messageId);
    setSourcesLoading(true);
    setSources([]);
    setChatError(null);

    try {
      const loadedSources =
        await getChatMessageSources(
          sessionId,
          messageId,
        );

      if (
        sourceRequestIdRef.current !==
        requestId
      ) {
        return;
      }

      setSources(loadedSources);
    } catch (error) {
      if (
        sourceRequestIdRef.current !==
        requestId
      ) {
        return;
      }

      if (
        !handleAuthenticationFailure(error)
      ) {
        setSources([]);
        setChatError(
          "Bu cevabın kaynakları alınamadı.",
        );
      }
    } finally {
      if (
        sourceRequestIdRef.current ===
        requestId
      ) {
        setSourcesLoading(false);
      }
    }
  }

  async function handleSendMessage(
    content: string,
  ): Promise<void> {
    if (sendingMessage) {
      return;
    }

    if (
      selectedDocumentIds.length === 0
    ) {
      setChatError(
        "Mesaj göndermeden önce en az bir hazır belge seç.",
      );

      return;
    }

    const messageDocumentIds = [
      ...selectedDocumentIds,
    ];

    setSendingMessage(true);
    setChatError(null);
    setSources([]);
    setSelectedSourceMessageId(null);
    setSourcesLoading(false);

    sourceRequestIdRef.current += 1;

    try {
      let sessionId =
        activeSessionId;

      if (!sessionId) {
        const newSession =
          await handleCreateSession();

        if (!newSession) {
          return;
        }

        sessionId = newSession.id;
      }

      await attachDocumentsToChatSession(
        sessionId,
        messageDocumentIds,
      );

      const response =
        await sendChatMessage(
          sessionId,
          content,
        );

      setMessages(
        (currentMessages) => [
          ...currentMessages,
          response.user_message,
          response.assistant_message,
        ],
      );

      setSelectedDocumentIds(
        messageDocumentIds,
      );

      sourceRequestIdRef.current += 1;

      setSelectedSourceMessageId(
        response.assistant_message.id,
      );

      setSourcesLoading(false);
      setSources(response.sources);

      setSessions((currentSessions) => {
        const activeSession =
          currentSessions.find(
            (session) =>
              session.id === sessionId,
          );

        if (!activeSession) {
          return currentSessions;
        }

        return [
          activeSession,
          ...currentSessions.filter(
            (session) =>
              session.id !== sessionId,
          ),
        ];
      });
    } catch (error) {
      if (
        !handleAuthenticationFailure(error)
      ) {
        setChatError(
          getErrorMessage(error),
        );
      }
    } finally {
      setSendingMessage(false);
    }
  }

  if (authChecking) {
    return (
      <main className="auth-loading-screen">
        <img
          src="/brand/mobilisim-logo.png"
          alt="Mobilişim İletişim A.Ş."
        />

        <p>Oturum kontrol ediliyor...</p>
      </main>
    );
  }

  if (!currentUser) {
    return (
    <AuthScreen
  dark={dark}
  submitting={authSubmitting}
  error={authError}
  onLogin={handleLogin}
  onRegister={handleRegister}
  onClearError={() =>
    setAuthError(null)
  }
  onThemeToggle={toggleTheme}
/>
    );
  }

  return (
    <div className="application-shell">
      <AppHeader
        user={currentUser}
        dark={dark}
        sourcePanelOpen={
          sourcePanelOpen
        }
        loggingOut={loggingOut}
        onLogout={handleLogout}
        onThemeToggle={toggleTheme}
        onSourcePanelToggle={() =>
          setSourcePanelOpen(
            (currentValue) =>
              !currentValue,
          )
        }
      />

      <div
        className={`workspace-layout ${
          sourcePanelOpen
            ? ""
            : "source-panel-hidden"
        }`}
      >
        <aside className="source-sidebar">
          <SourceSidebar
            documents={documents}
            sessions={sessions}
            selectedDocumentIds={
              selectedDocumentIds
            }
            activeSessionId={
              activeSessionId
            }
            loading={initialLoading}
            creatingSession={
              creatingSession
            }
            deletingDocumentId={
              deletingDocumentId
            }
            deletingSessionId={
              deletingSessionId
            }
            renamingSessionId={
              renamingSessionId
            }
            error={sidebarError}
            onUploadClick={() =>
              setUploadModalOpen(true)
            }
            onDocumentToggle={
              toggleDocument
            }
            onDeleteDocument={
              handleDeleteDocument
            }
            onSessionSelect={
              setActiveSessionId
            }
            onRenameSession={
              handleRenameSession
            }
            onDeleteSession={
              handleDeleteSession
            }
            onCreateSession={
              handleCreateSession
            }
          />
        </aside>

        <main className="chat-workspace">
          <ChatWorkspace
            messages={messages}
            selectedSourceMessageId={
              selectedSourceMessageId
            }
            sourcesLoading={sourcesLoading}
            selectedDocumentCount={
              selectedDocumentIds.length
            }
            loading={messagesLoading}
            sending={sendingMessage}
            error={chatError}
            onSendMessage={
              handleSendMessage
            }
            onAssistantMessageSelect={
              handleAssistantMessageSelect
            }
            onUploadClick={() =>
              setUploadModalOpen(true)
            }
          />
        </main>

        {sourcePanelOpen && (
          <aside className="source-inspector">
            <SourceInspector
              sources={sources}
            />
          </aside>
        )}
      </div>

      <WorkspaceDialog
        dialog={workspaceDialog}
        busy={workspaceDialogBusy}
        error={sidebarError}
        onClose={() => {
          if (!workspaceDialogBusy) {
            setWorkspaceDialog(null);
            setSidebarError(null);
          }
        }}
        onConfirm={confirmWorkspaceDialog}
      />

      <UploadModal
        open={uploadModalOpen}
        onClose={() =>
          setUploadModalOpen(false)
        }
        onUpload={handleUpload}
      />
    </div>
  );
}

export default App;
