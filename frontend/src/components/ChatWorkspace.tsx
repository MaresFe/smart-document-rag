import { useRef, useState } from "react";

import {
  ArrowUp,
  FileSearch,
  Lightbulb,
  ListChecks,
  LoaderCircle,
  MessageSquareText,
  Paperclip,
  Sparkles,
} from "lucide-react";

import type { ChatMessageRead } from "../types";

interface ChatWorkspaceProps {
  messages: ChatMessageRead[];
  selectedDocumentCount: number;
  loading: boolean;
  sending: boolean;
  error: string | null;
  onSendMessage: (content: string) => Promise<void>;
  onUploadClick: () => void;
}

const suggestions = [
  {
    id: "key-points",
    icon: <ListChecks size={18} />,
    title: "Ana maddeleri çıkar",
    description: "Seçili belgelerdeki en önemli noktaları listele.",
    prompt:
      "Seçili belgelerdeki en önemli maddeleri kısa ve anlaşılır biçimde listele.",
  },
  {
    id: "summarize",
    icon: <FileSearch size={18} />,
    title: "Belgeyi özetle",
    description: "İçeriği kısa ve anlaşılır biçimde özetle.",
    prompt:
      "Seçili belgelerin ana konularını ve önemli sonuçlarını özetle.",
  },
  {
    id: "explain",
    icon: <Lightbulb size={18} />,
    title: "Kavramları açıkla",
    description: "Teknik terimleri bağlamıyla birlikte açıkla.",
    prompt:
      "Seçili belgelerde geçen önemli teknik kavramları basit bir dille açıkla.",
  },
];

function ChatWorkspace({
  messages,
  selectedDocumentCount,
  loading,
  sending,
  error,
  onSendMessage,
  onUploadClick,
}: ChatWorkspaceProps) {
  const [prompt, setPrompt] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const canSubmit =
    prompt.trim().length > 0 &&
    selectedDocumentCount > 0 &&
    !sending;

  function selectSuggestion(suggestionPrompt: string) {
    setPrompt(suggestionPrompt);

    requestAnimationFrame(() => {
      textareaRef.current?.focus();
      textareaRef.current?.setSelectionRange(
        suggestionPrompt.length,
        suggestionPrompt.length,
      );
    });
  }

  async function submitPrompt() {
    const normalizedPrompt = prompt.trim();

    if (!normalizedPrompt || sending) {
      return;
    }

    if (selectedDocumentCount === 0) {
      return;
    }

    setPrompt("");

    await onSendMessage(normalizedPrompt);
  }

  return (
    <div className="chat-workspace-content">
      <section className="chat-hero">
        <div className="chat-hero-icon">
          <Sparkles size={23} />
        </div>

        <div>
          <p className="eyebrow">Belge Asistanı</p>
          <h1>Belgelerinle konuş.</h1>

          <p className="chat-hero-description">
            Seçili kaynaklar üzerinde semantik arama yap, özet çıkar
            ve güvenilir yanıtları kaynaklarıyla birlikte incele.
          </p>
        </div>
      </section>

      {loading ? (
        <section className="chat-loading-state">
          <LoaderCircle className="spinning-icon" size={24} />
          <span>Sohbet geçmişi yükleniyor...</span>
        </section>
      ) : messages.length === 0 ? (
        <section className="suggestion-section">
          <div className="section-heading-row">
            <div>
              <h2>Başlamak için bir soru seç</h2>

              <p>
                İstersen aşağıdaki örneklerden biriyle başlayabilirsin.
              </p>
            </div>

            <span className="source-count-badge">
              <MessageSquareText size={14} />
              {selectedDocumentCount} kaynak seçili
            </span>
          </div>

          <div className="suggestion-grid">
            {suggestions.map((suggestion) => (
              <button
                key={suggestion.id}
                className="suggestion-card"
                type="button"
                disabled={selectedDocumentCount === 0}
                onClick={() => selectSuggestion(suggestion.prompt)}
              >
                <span className="suggestion-icon">
                  {suggestion.icon}
                </span>

                <span className="suggestion-copy">
                  <strong>{suggestion.title}</strong>
                  <span>{suggestion.description}</span>
                </span>
              </button>
            ))}
          </div>
        </section>
      ) : (
        <section className="real-conversation">
          {messages.map((message) =>
            message.role === "user" ? (
              <div
                className="demo-user-message"
                key={message.id}
              >
                <span>Sen</span>
                <p>{message.content}</p>
              </div>
            ) : (
              <div
                className="demo-assistant-message"
                key={message.id}
              >
                <div className="demo-assistant-avatar">
                  <Sparkles size={18} />
                </div>

                <div>
                  <span>Belge Asistanı</span>
                  <p>{message.content}</p>
                </div>
              </div>
            ),
          )}

          {sending && (
            <div className="demo-assistant-message">
              <div className="demo-assistant-avatar">
                <LoaderCircle
                  className="spinning-icon"
                  size={18}
                />
              </div>

              <div>
                <span>Belge Asistanı</span>
                <p>Belgeler inceleniyor ve yanıt hazırlanıyor...</p>
              </div>
            </div>
          )}
        </section>
      )}

      {error && (
        <div className="chat-api-error" role="alert">
          {error}
        </div>
      )}

      {selectedDocumentCount === 0 && (
        <div className="chat-selection-warning">
          Mesaj göndermek için sol panelden en az bir hazır belge seç.
        </div>
      )}

      <div className="chat-spacer" />

      <section className="composer-wrapper">
        <div className="composer-shell">
          <textarea
            ref={textareaRef}
            value={prompt}
            aria-label="Belgeler hakkında soru sor"
            placeholder="Belgeler hakkında soru sor..."
            rows={2}
            disabled={sending}
            onChange={(event) => setPrompt(event.target.value)}
        onKeyDown={(event) => {
  if (
    event.key === "Enter" &&
    !event.shiftKey &&
    !event.nativeEvent.isComposing
  ) {
    event.preventDefault();
    void submitPrompt();
  }
}}
          />

          <div className="composer-footer">
            <button
              className="composer-action"
              type="button"
              aria-label="Dosya ekle"
              title="Dosya ekle"
              onClick={onUploadClick}
            >
              <Paperclip size={18} />
            </button>

            <span className="composer-hint">
              {sending
                ? "Yanıt hazırlanıyor..."
                : prompt.length > 0
? `${prompt.length} karakter · Enter gönderir · Shift + Enter yeni satır`
: "Yanıtlar yalnızca seçili kaynaklara dayanır."}
            </span>

            <button
              className="send-button"
              type="button"
              aria-label="Soruyu gönder"
              title="Gönder"
              disabled={!canSubmit}
              onClick={() => {
                void submitPrompt();
              }}
            >
              {sending ? (
                <LoaderCircle
                  className="spinning-icon"
                  size={19}
                />
              ) : (
                <ArrowUp size={19} strokeWidth={2.4} />
              )}
            </button>
          </div>
        </div>

        <p className="composer-disclaimer">
          Yapay zekâ yanıtlarını kritik kullanım öncesinde doğrulayın.
        </p>
      </section>
    </div>
  );
}

export default ChatWorkspace;