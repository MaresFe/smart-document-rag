import {
  BookOpenText,
  CircleHelp,
  PanelRight,
  Sparkles,
} from "lucide-react";

import ThemeToggle from "./ThemeToggle";

interface AppHeaderProps {
  dark: boolean;
  sourcePanelOpen: boolean;
  onThemeToggle: () => void;
  onSourcePanelToggle: () => void;
}

function AppHeader({
  dark,
  sourcePanelOpen,
  onThemeToggle,
  onSourcePanelToggle,
}: AppHeaderProps) {
  return (
    <header className="app-header">
      <div className="brand">
        <div className="brand-mark" aria-hidden="true">
          <BookOpenText size={22} strokeWidth={2.2} />
        </div>

        <div className="brand-copy">
          <div className="brand-title-row">
            <span className="brand-title">Smart Document RAG</span>

            <span className="brand-badge">
              <Sparkles size={12} />
              AI Workspace
            </span>
          </div>

          <span className="brand-subtitle">
            Belgelerinizden güvenilir ve kaynaklı yanıtlar
          </span>
        </div>
      </div>

      <div className="header-actions">
        <button
          className="icon-button"
          type="button"
          aria-label="Yardım"
          title="Yardım"
        >
          <CircleHelp size={19} />
        </button>

        <button
          className={`icon-button ${
            sourcePanelOpen ? "icon-button-active" : ""
          }`}
          type="button"
          aria-label="Kaynak panelini aç veya kapat"
          title="Kaynak paneli"
          onClick={onSourcePanelToggle}
        >
          <PanelRight size={19} />
        </button>

        <ThemeToggle dark={dark} onToggle={onThemeToggle} />
      </div>
    </header>
  );
}

export default AppHeader;