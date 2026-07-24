import { useCallback, useEffect, useState } from "react";

import "./App.css";

import AppHeader from "./components/AppHeader";
import ChatWorkspace from "./components/ChatWorkspace";
import SourceInspector from "./components/SourceInspector";
import SourceSidebar from "./components/SourceSidebar";
import UploadModal from "./components/UploadModal";

import {
  attachDocumentsToChatSession,
  createChatSession,
  deleteChatSession,
  deleteDocument,
  getChatMessages,
  getChatSessions,
  getDocuments,
  sendChatMessage,
  updateChatSession,
  uploadDocument,
} from "./services/api";

import type {
  ChatMessageRead,
  ChatSessionRead,
  ChatSourceRead,
  DocumentRead,
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

  const [sourcePanelOpen, setSourcePanelOpen] =
    useState(true);

  const [uploadModalOpen, setUploadModalOpen] =
    useState(false);

  const [documents, setDocuments] =
    useState<DocumentRead[]>([]);

  const [sessions, setSessions] =
    useState<ChatSessionRead[]>([]);

  const [messages, setMessages] =
    useState<ChatMessageRead[]>([]);

  const [sources, setSources] =
    useState<ChatSourceRead[]>([]);

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

  useEffect(() => {
    document.documentElement.dataset.theme = theme;

    localStorage.setItem(
      "smart-rag-theme",
      theme,
    );
  }, [theme]);

  const loadDocuments = useCallback(async () => {
    const loadedDocuments = await getDocuments();

    setDocuments(loadedDocuments);

    setSelectedDocumentIds((currentIds) => {
      const availableIds = new Set(
        loadedDocuments
          .filter(
            (document) =>
              document.status === "ready",
          )
          .map((document) => document.id),
      );

      return currentIds.filter((id) =>
        availableIds.has(id),
      );
    });

    return loadedDocuments;
  }, []);

  const loadSessions = useCallback(async () => {
    const loadedSessions =
      await getChatSessions();

    setSessions(loadedSessions);

    return loadedSessions;
  }, []);

  useEffect(() => {
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

        if (loadedSessions.length > 0) {
          setActiveSessionId(
            loadedSessions[0].id,
          );
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
        setSidebarError(
          getErrorMessage(error),
        );
      } finally {
        setInitialLoading(false);
      }
    }

    void initializeApplication();
  }, [loadDocuments, loadSessions]);

  useEffect(() => {
    setSources([]);

    if (!activeSessionId) {
      setMessages([]);
      return;
    }

    const sessionId = activeSessionId;

    async function loadMessages() {
      setMessagesLoading(true);
      setChatError(null);

      try {
        const loadedMessages =
          await getChatMessages(sessionId);

        setMessages(loadedMessages);
      } catch (error) {
        setChatError(
          getErrorMessage(error),
        );
      } finally {
        setMessagesLoading(false);
      }
    }

    void loadMessages();
  }, [activeSessionId]);

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

    const documentToDelete = documents.find(
      (document) =>
        document.id === documentId,
    );

    if (!documentToDelete) {
      return;
    }

    const confirmed = window.confirm(
      `"${documentToDelete.original_filename}" belgesini silmek istediğine emin misin?\n\nBu işlem geri alınamaz.`,
    );

    if (!confirmed) {
      return;
    }

    setDeletingDocumentId(documentId);
    setSidebarError(null);

    try {
      await deleteDocument(documentId);

      setDocuments((currentDocuments) =>
        currentDocuments.filter(
          (document) =>
            document.id !== documentId,
        ),
      );

      setSelectedDocumentIds(
        (currentIds) =>
          currentIds.filter(
            (id) => id !== documentId,
          ),
      );

      setSources((currentSources) =>
        currentSources.filter(
          (source) =>
            source.document_id !==
            documentId,
        ),
      );
    } catch (error) {
      setSidebarError(
        getErrorMessage(error),
      );
    } finally {
      setDeletingDocumentId(null);
    }
  }

  async function handleDeleteSession(
    sessionId: string,
  ): Promise<void> {
    if (deletingSessionId) {
      return;
    }

    const sessionToDelete = sessions.find(
      (session) =>
        session.id === sessionId,
    );

    if (!sessionToDelete) {
      return;
    }

    const sessionTitle =
      sessionToDelete.title ||
      "Başlıksız sohbet";

    const confirmed = window.confirm(
      `"${sessionTitle}" sohbetini silmek istediğine emin misin?\n\nBu işlem geri alınamaz.`,
    );

    if (!confirmed) {
      return;
    }

    setDeletingSessionId(sessionId);
    setSidebarError(null);

    try {
      await deleteChatSession(sessionId);

      const remainingSessions =
        sessions.filter(
          (session) =>
            session.id !== sessionId,
        );

      setSessions(remainingSessions);

      if (
        activeSessionId === sessionId
      ) {
        const nextSession =
          remainingSessions[0] ?? null;

        setActiveSessionId(
          nextSession?.id ?? null,
        );

        setMessages([]);
        setSources([]);
      }
    } catch (error) {
      setSidebarError(
        getErrorMessage(error),
      );
    } finally {
      setDeletingSessionId(null);
    }
  }

  async function handleRenameSession(
    sessionId: string,
  ): Promise<void> {
    if (renamingSessionId) {
      return;
    }

    const sessionToRename = sessions.find(
      (session) =>
        session.id === sessionId,
    );

    if (!sessionToRename) {
      return;
    }

    const currentTitle =
      sessionToRename.title ||
      "Başlıksız sohbet";

    const requestedTitle = window.prompt(
      "Sohbet için yeni bir ad gir:",
      currentTitle,
    );

    if (requestedTitle === null) {
      return;
    }

    const normalizedTitle =
      requestedTitle.trim();

    if (!normalizedTitle) {
      setSidebarError(
        "Sohbet adı boş bırakılamaz.",
      );
      return;
    }

    if (
      normalizedTitle === currentTitle
    ) {
      return;
    }

    setRenamingSessionId(sessionId);
    setSidebarError(null);

    try {
      const updatedSession =
        await updateChatSession(
          sessionId,
          {
            title: normalizedTitle,
          },
        );

      setSessions((currentSessions) =>
        currentSessions.map((session) =>
          session.id === sessionId
            ? updatedSession
            : session,
        ),
      );
    } catch (error) {
      setSidebarError(
        getErrorMessage(error),
      );
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

      setSessions((currentSessions) => [
        session,
        ...currentSessions.filter(
          (currentSession) =>
            currentSession.id !==
            session.id,
        ),
      ]);

      setActiveSessionId(session.id);
      setMessages([]);
      setSources([]);

      return session;
    } catch (error) {
      setSidebarError(
        getErrorMessage(error),
      );

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
      setSidebarError(
        getErrorMessage(error),
      );

      throw error;
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

    setSendingMessage(true);
    setChatError(null);
    setSources([]);

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
        selectedDocumentIds,
      );

      const response =
        await sendChatMessage(
          sessionId,
          content,
        );

      setMessages((currentMessages) => [
        ...currentMessages,
        response.user_message,
        response.assistant_message,
      ]);

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
      setChatError(
        getErrorMessage(error),
      );
    } finally {
      setSendingMessage(false);
    }
  }

  return (
    <div className="application-shell">
      <AppHeader
        dark={dark}
        sourcePanelOpen={
          sourcePanelOpen
        }
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
            selectedDocumentCount={
              selectedDocumentIds.length
            }
            loading={messagesLoading}
            sending={sendingMessage}
            error={chatError}
            onSendMessage={
              handleSendMessage
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