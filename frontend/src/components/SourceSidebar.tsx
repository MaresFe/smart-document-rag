import { useMemo, useState } from "react";

import {
  Check,
  Clock3,
  FileText,
  MessageSquare,
  MessageSquarePlus,
  MoreHorizontal,
  Plus,
  Search,
  Upload,
} from "lucide-react";

interface DocumentItem {
  id: string;
  name: string;
  type: string;
  size: string;
}

interface ConversationItem {
  id: string;
  title: string;
  updatedAt: string;
}

const initialDocuments: DocumentItem[] = [
  {
    id: "document-1",
    name: "company.pdf",
    type: "PDF",
    size: "2.4 MB",
  },
  {
    id: "document-2",
    name: "rag-notes.docx",
    type: "DOCX",
    size: "860 KB",
  },
  {
    id: "document-3",
    name: "architecture.pdf",
    type: "PDF",
    size: "1.2 MB",
  },
];

const initialConversations: ConversationItem[] = [
  {
    id: "conversation-1",
    title: "Embedding yapısı",
    updatedAt: "Az önce",
  },
  {
    id: "conversation-2",
    title: "Şirket hizmetleri özeti",
    updatedAt: "18 dk önce",
  },
  {
    id: "conversation-3",
    title: "Backend mimarisi",
    updatedAt: "Dün",
  },
];

interface SourceSidebarProps {
  onUploadClick: () => void;
}

function SourceSidebar({
  onUploadClick,
}: SourceSidebarProps) {  
    const [searchValue, setSearchValue] = useState("");
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([
    "document-1",
    "document-2",
  ]);

  const [conversations, setConversations] =
    useState<ConversationItem[]>(initialConversations);

  const [activeConversationId, setActiveConversationId] = useState(
    "conversation-1",
  );

  const filteredDocuments = useMemo(() => {
    const normalizedSearch = searchValue.trim().toLocaleLowerCase("tr");

    if (!normalizedSearch) {
      return initialDocuments;
    }

    return initialDocuments.filter((document) =>
      document.name.toLocaleLowerCase("tr").includes(normalizedSearch),
    );
  }, [searchValue]);

  function toggleDocument(documentId: string) {
    setSelectedDocumentIds((currentIds) => {
      if (currentIds.includes(documentId)) {
        return currentIds.filter((id) => id !== documentId);
      }

      return [...currentIds, documentId];
    });
  }

  function createConversation() {
    const conversationId = crypto.randomUUID();

    const newConversation: ConversationItem = {
      id: conversationId,
      title: "Yeni sohbet",
      updatedAt: "Şimdi",
    };

    setConversations((currentConversations) => [
      newConversation,
      ...currentConversations,
    ]);

    setActiveConversationId(conversationId);
  }

  return (
    <div className="source-sidebar-content">
      <div className="sidebar-heading">
        <div>
          <p className="eyebrow">Çalışma Alanı</p>
          <h2>Kaynaklar</h2>
        </div>

        <button
          className="small-icon-button"
          type="button"
          aria-label="Yeni kaynak ekle"
          title="Yeni kaynak ekle"
        >
          <Plus size={17} />
        </button>
      </div>

      <p className="sidebar-description">
        Sorularınız yalnızca seçili belgeler üzerinden yanıtlanır.
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
          onChange={(event) => setSearchValue(event.target.value)}
        />
      </label>

      <div className="source-list-header">
        <span>Belgeler</span>

        <span>
          {selectedDocumentIds.length} / {initialDocuments.length} seçili
        </span>
      </div>

      <div className="document-list">
        {filteredDocuments.length > 0 ? (
          filteredDocuments.map((document) => {
            const selected = selectedDocumentIds.includes(document.id);

            return (
              <button
                key={document.id}
                className={`document-item ${
                  selected ? "document-item-selected" : ""
                }`}
                type="button"
                aria-pressed={selected}
                onClick={() => toggleDocument(document.id)}
              >
                <span className="document-check">
                  {selected && <Check size={13} strokeWidth={3} />}
                </span>

                <span className="document-icon">
                  <FileText size={18} />
                </span>

                <span className="document-copy">
                  <span className="document-name">{document.name}</span>

                  <span className="document-meta">
                    {document.type} · {document.size}
                  </span>
                </span>

                <span className="document-menu" aria-hidden="true">
                  <MoreHorizontal size={17} />
                </span>
              </button>
            );
          })
        ) : (
          <div className="sidebar-empty-state">
            <Search size={18} />
            <span>Eşleşen kaynak bulunamadı.</span>
          </div>
        )}
      </div>

      <div className="sidebar-divider" />

      <section className="conversation-section">
        <div className="conversation-heading">
          <div>
            <p className="eyebrow">Geçmiş</p>
            <h3>Sohbetler</h3>
          </div>

          <button
            className="small-icon-button"
            type="button"
            aria-label="Yeni sohbet oluştur"
            title="Yeni sohbet"
            onClick={createConversation}
          >
            <MessageSquarePlus size={17} />
          </button>
        </div>

        <div className="conversation-list">
          {conversations.map((conversation) => {
            const active = conversation.id === activeConversationId;

            return (
              <button
                key={conversation.id}
                className={`conversation-item ${
                  active ? "conversation-item-active" : ""
                }`}
                type="button"
                aria-current={active ? "true" : undefined}
                onClick={() => setActiveConversationId(conversation.id)}
              >
                <span className="conversation-icon">
                  <MessageSquare size={16} />
                </span>

                <span className="conversation-copy">
                  <strong>{conversation.title}</strong>

                  <span>
                    <Clock3 size={11} />
                    {conversation.updatedAt}
                  </span>
                </span>

                <span className="conversation-menu" aria-hidden="true">
                  <MoreHorizontal size={16} />
                </span>
              </button>
            );
          })}
        </div>
      </section>

      <div className="sidebar-footer-card">
        <div className="sidebar-footer-icon">
          <FileText size={18} />
        </div>

        <div>
          <strong>{initialDocuments.length} kaynak hazır</strong>

          <span>
            {selectedDocumentIds.length} kaynak aktif olarak kullanılıyor.
          </span>
        </div>
      </div>
    </div>
  );
}

export default SourceSidebar;