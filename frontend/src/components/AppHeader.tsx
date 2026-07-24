import { PanelRight } from "lucide-react";

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
        <img
          className="brand-logo"
          src="/brand/mobilisim-logo.png"
          alt="Mobilisim İletişim A.Ş."
        />

        <span
          className="brand-divider"
          aria-hidden="true"
        />

        <div className="brand-copy">
          <span className="brand-title">
            Smart Document RAG
          </span>

          <span className="brand-subtitle">
            Belge tabanlı bilgi asistanı
          </span>
        </div>
      </div>

      <div className="header-actions">
        <button
          className={`icon-button ${
            sourcePanelOpen
              ? "icon-button-active"
              : ""
          }`}
          type="button"
          aria-label="Kaynak panelini aç veya kapat"
          title="Kaynak paneli"
          onClick={onSourcePanelToggle}
        >
          <PanelRight size={19} />
        </button>

        <ThemeToggle
          dark={dark}
          onToggle={onThemeToggle}
        />
      </div>
    </header>
  );
}

export default AppHeader;