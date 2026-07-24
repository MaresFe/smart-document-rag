import { useEffect, useMemo, useState } from "react";

import {
  Check,
  Clock3,
  FileText,
  LoaderCircle,
  MessageSquare,
  MessageSquarePlus,
  MoreHorizontal,
  Search,
  Trash2,
  Upload,
} from "lucide-react";

import type {
  ChatSessionRead,
  DocumentRead,
} from "../types";

interface SourceSidebarProps {
  documents: DocumentRead[];
  sessions: ChatSessionRead[];
  selectedDocumentIds: string[];
  activeSessionId: string | null;
  loading: boolean;
  creatingSession: boolean;
  deletingDocumentId: string | null;
  deletingSessionId: string | null;
  renamingSessionId: string | null;
  error: string | null;
  onUploadClick: () => void;
  onDocumentToggle: (documentId: string) => void;
  onDeleteDocument: (documentId: string) => Promise<void>;
  onSessionSelect: (sessionId: string) => void;
  onRenameSession: (sessionId: string) => Promise<void>;
  onDeleteSession: (sessionId: string) => Promise<void>;
  onCreateSession: () => Promise<ChatSessionRead | null>;
}

function formatFileSize(size: number | null): string {
  if (size === null) {
    return "Boyut bilinmiyor";
  }

  if (size < 1024) {
    return `${size} B`;
  }

  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(0)} KB`;
  }

  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function formatRelativeDate(dateValue: string): string {
  const date = new Date(dateValue);
  const difference = Date.now() - date.getTime();

  if (Number.isNaN(date.getTime())) {
    return "";
  }

  const minute = 60 * 1000;
  const hour = 60 * minute;
  const day = 24 * hour;

  if (difference < minute) {
    return "Şimdi";
  }

  if (difference < hour) {
    return `${Math.floor(difference / minute)} dk önce`;
  }

  if (difference < day) {
    return `${Math.floor(difference / hour)} sa önce`;
  }

  if (difference < day * 2) {
    return "Dün";
  }

  return date.toLocaleDateString("tr-TR", {
    day: "numeric",
    month: "short",
  });
}

function getDocumentStatusLabel(
  document: DocumentRead,
): string {
  if (document.status === "ready") {
    return `${document.file_type.toUpperCase()} · ${formatFileSize(
      document.file_size,
    )}`;
  }

  if (document.status === "processing") {
    return "İşleniyor";
  }

  if (document.status === "failed") {
    return "İşlenemedi";
  }

  return document.status;
}

function SourceSidebar({
  documents,
  sessions,
  selectedDocumentIds,
  activeSessionId,
  loading,
  creatingSession,
  deletingDocumentId,
  deletingSessionId,
  renamingSessionId,
  error,
  onUploadClick,
  onDocumentToggle,
  onDeleteDocument,
  onSessionSelect,
  onRenameSession,
  onDeleteSession,
  onCreateSession,
}: SourceSidebarProps) {
  const [searchValue, setSearchValue] = useState("");

  const [
    openDocumentMenuId,
    setOpenDocumentMenuId,
  ] = useState<string | null>(null);

  const [
    openSessionMenuId,
    setOpenSessionMenuId,
  ] = useState<string | null>(null);

  useEffect(() => {
    if (
      !openDocumentMenuId &&
      !openSessionMenuId
    ) {
      return;
    }

    function closeOpenMenus() {
      setOpenDocumentMenuId(null);
      setOpenSessionMenuId(null);
    }

    window.addEventListener(
      "click",
      closeOpenMenus,
    );

    return () => {
      window.removeEventListener(
        "click",
        closeOpenMenus,
      );
    };
  }, [
    openDocumentMenuId,
    openSessionMenuId,
  ]);

  const filteredDocuments = useMemo(() => {
    const normalizedSearch = searchValue
      .trim()
      .toLocaleLowerCase("tr");

    if (!normalizedSearch) {
      return documents;
    }

    return documents.filter((document) =>
      document.original_filename
        .toLocaleLowerCase("tr")
        .includes(normalizedSearch),
    );
  }, [documents, searchValue]);

  const readyDocumentCount = documents.filter(
    (document) =>
      document.status === "ready",
  ).length;

  return (
    <div className="source-sidebar-content">
      <div className="sidebar-heading">
        <div>
          <p className="eyebrow">
            Çalışma Alanı
          </p>

          <h2>Kaynaklar</h2>
        </div>
      </div>

      <p className="sidebar-description">
        Sorularınız yalnızca seçili belgeler
        üzerinden yanıtlanır.
      </p>

      <button
        className="primary-btn"
        type="button"
        onClick={onUploadClick}
      >
        <Upload size={17} />
        Doküman yükle
      </button>

      <label className="sidebar-search">
        <Search size={16} />

        <input
          type="search"
          value={searchValue}
          placeholder="Kaynaklarda ara"
          aria-label="Kaynaklarda ara"
          onChange={(event) =>
            setSearchValue(
              event.target.value,
            )
          }
        />
      </label>

      <div className="source-list-header">
        <span>Belgeler</span>

        <span>
          {selectedDocumentIds.length} /{" "}
          {documents.length} seçili
        </span>
      </div>

      <div className="document-list">
        {loading ? (
          <div className="sidebar-empty-state">
            <LoaderCircle
              className="spinning-icon"
              size={18}
            />

            <span>
              Belgeler yükleniyor...
            </span>
          </div>
        ) : filteredDocuments.length > 0 ? (
          filteredDocuments.map(
            (document) => {
              const selected =
                selectedDocumentIds.includes(
                  document.id,
                );

              const selectable =
                document.status === "ready";

              const deleting =
                deletingDocumentId ===
                document.id;

              const menuOpen =
                openDocumentMenuId ===
                document.id;

              return (
                <div
                  key={document.id}
                  className={`document-item ${
                    selected
                      ? "document-item-selected"
                      : ""
                  }`}
                >
                  <button
                    className="document-main-button"
                    type="button"
                    aria-pressed={selected}
                    disabled={
                      !selectable ||
                      deleting
                    }
                    title={
                      document.status ===
                      "failed"
                        ? document.error_message ??
                          "Belge işlenemedi."
                        : undefined
                    }
                    onClick={() =>
                      onDocumentToggle(
                        document.id,
                      )
                    }
                  >
                    <span className="document-check">
                      {selected && (
                        <Check
                          size={13}
                          strokeWidth={3}
                        />
                      )}
                    </span>

                    <span className="document-icon">
                      <FileText size={18} />
                    </span>

                    <span className="document-copy">
                      <span className="document-name">
                        {
                          document.original_filename
                        }
                      </span>

                      <span className="document-meta">
                        {deleting
                          ? "Siliniyor..."
                          : getDocumentStatusLabel(
                              document,
                            )}
                      </span>
                    </span>
                  </button>

                  <div className="document-menu-wrapper">
                    <button
                      className="document-menu-button"
                      type="button"
                      aria-label={`${document.original_filename} seçenekleri`}
                      aria-haspopup="menu"
                      aria-expanded={
                        menuOpen
                      }
                      disabled={deleting}
                      onClick={(event) => {
                        event.stopPropagation();

                        setOpenSessionMenuId(
                          null,
                        );

                        setOpenDocumentMenuId(
                          menuOpen
                            ? null
                            : document.id,
                        );
                      }}
                    >
                      {deleting ? (
                        <LoaderCircle
                          className="spinning-icon"
                          size={16}
                        />
                      ) : (
                        <MoreHorizontal
                          size={17}
                        />
                      )}
                    </button>

                    {menuOpen && (
                      <div
                        className="document-menu-popover"
                        role="menu"
                        onClick={(event) =>
                          event.stopPropagation()
                        }
                      >
                        <button
                          className="document-delete-action"
                          type="button"
                          role="menuitem"
                          disabled={deleting}
                          onClick={(event) => {
                            event.stopPropagation();

                            setOpenDocumentMenuId(
                              null,
                            );

                            void onDeleteDocument(
                              document.id,
                            );
                          }}
                        >
                          <Trash2 size={15} />
                          Belgeyi sil
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              );
            },
          )
        ) : (
          <div className="sidebar-empty-state">
            <Search size={18} />

            <span>
              {documents.length === 0
                ? "Henüz doküman yüklenmedi."
                : "Eşleşen kaynak bulunamadı."}
            </span>
          </div>
        )}
      </div>

      {error && (
        <div
          className="sidebar-api-error"
          role="alert"
        >
          {error}
        </div>
      )}

      <div className="sidebar-divider" />

      <section className="conversation-section">
        <div className="conversation-heading">
          <div>
            <p className="eyebrow">
              Geçmiş
            </p>

            <h3>Sohbetler</h3>
          </div>

          <button
            className="small-icon-button"
            type="button"
            aria-label="Yeni sohbet oluştur"
            title="Yeni sohbet"
            disabled={creatingSession}
            onClick={() => {
              void onCreateSession();
            }}
          >
            {creatingSession ? (
              <LoaderCircle
                className="spinning-icon"
                size={17}
              />
            ) : (
              <MessageSquarePlus
                size={17}
              />
            )}
          </button>
        </div>

        <div className="conversation-list">
          {sessions.length > 0 ? (
            sessions.map((session) => {
              const active =
                session.id ===
                activeSessionId;

              const deleting =
                session.id ===
                deletingSessionId;

              const renaming =
                session.id ===
                renamingSessionId;

              const busy =
                deleting || renaming;

              const menuOpen =
                session.id ===
                openSessionMenuId;

              return (
                <div
                  key={session.id}
                  className={`conversation-item ${
                    active
                      ? "conversation-item-active"
                      : ""
                  }`}
                >
                  <button
                    className="conversation-main-button"
                    type="button"
                    aria-current={
                      active
                        ? "true"
                        : undefined
                    }
                    disabled={busy}
                    onClick={() =>
                      onSessionSelect(
                        session.id,
                      )
                    }
                  >
                    <span className="conversation-icon">
                      <MessageSquare
                        size={16}
                      />
                    </span>

                    <span className="conversation-copy">
                      <strong>
                        {session.title ||
                          "Başlıksız sohbet"}
                      </strong>

                      <span>
                        <Clock3 size={11} />

                        {deleting
                          ? "Siliniyor..."
                          : renaming
                            ? "Yeniden adlandırılıyor..."
                            : formatRelativeDate(
                                session.created_at,
                              )}
                      </span>
                    </span>
                  </button>

                  <div className="conversation-menu-wrapper">
                    <button
                      className="conversation-menu-button"
                      type="button"
                      aria-label={`${
                        session.title ||
                        "Başlıksız sohbet"
                      } seçenekleri`}
                      aria-haspopup="menu"
                      aria-expanded={
                        menuOpen
                      }
                      disabled={busy}
                      onClick={(event) => {
                        event.stopPropagation();

                        setOpenDocumentMenuId(
                          null,
                        );

                        setOpenSessionMenuId(
                          menuOpen
                            ? null
                            : session.id,
                        );
                      }}
                    >
                      {busy ? (
                        <LoaderCircle
                          className="spinning-icon"
                          size={16}
                        />
                      ) : (
                        <MoreHorizontal
                          size={16}
                        />
                      )}
                    </button>

                    {menuOpen && (
                      <div
                        className="conversation-menu-popover"
                        role="menu"
                        onClick={(event) =>
                          event.stopPropagation()
                        }
                      >
                        <button
                          className="conversation-rename-action"
                          type="button"
                          role="menuitem"
                          disabled={busy}
                          onClick={(event) => {
                            event.stopPropagation();

                            setOpenSessionMenuId(
                              null,
                            );

                            void onRenameSession(
                              session.id,
                            );
                          }}
                        >
                          Yeniden adlandır
                        </button>

                        <button
                          className="conversation-delete-action"
                          type="button"
                          role="menuitem"
                          disabled={busy}
                          onClick={(event) => {
                            event.stopPropagation();

                            setOpenSessionMenuId(
                              null,
                            );

                            void onDeleteSession(
                              session.id,
                            );
                          }}
                        >
                          <Trash2 size={15} />
                          Sohbeti sil
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          ) : (
            <div className="sidebar-empty-state">
              <MessageSquare size={18} />

              <span>
                Henüz sohbet oluşturulmadı.
              </span>
            </div>
          )}
        </div>
      </section>

      <div className="sidebar-footer-card">
        <div className="sidebar-footer-icon">
          <FileText size={18} />
        </div>

        <div>
          <strong>
            {readyDocumentCount} kaynak hazır
          </strong>

          <span>
            {selectedDocumentIds.length} kaynak
            aktif olarak kullanılıyor.
          </span>
        </div>
      </div>
    </div>
  );
}

export default SourceSidebar;