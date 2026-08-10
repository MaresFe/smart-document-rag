import { PanelRight, Users } from "lucide-react";
import { useState } from "react";

import type { UserRead } from "../types";

import AdminUserPanel from "./AdminUserPanel";
import ThemeToggle from "./ThemeToggle";


interface AppHeaderProps {
  user: UserRead;
  dark: boolean;
  sourcePanelOpen: boolean;
  loggingOut: boolean;
  onLogout: () => Promise<void>;
  onThemeToggle: () => void;
  onSourcePanelToggle: () => void;
}


function AppHeader({
  user,
  dark,
  sourcePanelOpen,
  loggingOut,
  onLogout,
  onThemeToggle,
  onSourcePanelToggle,
}: AppHeaderProps) {
  const [adminPanelOpen, setAdminPanelOpen] =
    useState(false);

  const displayName =
    user.full_name?.trim() || user.email;

  return (
    <>
      <header className="app-header">
        <div className="brand">
          <img
            className="brand-logo"
            src="/brand/mobilisim-logo.png"
            alt="Mobilişim İletişim A.Ş."
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
          <div className="header-account">
            <div className="header-account-copy">
              <strong>{displayName}</strong>
              <span>{user.email}</span>
            </div>

            <button
              className="header-logout-button"
              type="button"
              disabled={loggingOut}
              onClick={() => {
                void onLogout();
              }}
            >
              {loggingOut
                ? "Çıkış yapılıyor..."
                : "Çıkış"}
            </button>
          </div>

          {user.is_admin && (
            <button
              className={`icon-button ${
                adminPanelOpen
                  ? "icon-button-active"
                  : ""
              }`}
              type="button"
              aria-label="Kullanıcı yönetimini aç"
              title="Kullanıcı yönetimi"
              onClick={() => setAdminPanelOpen(true)}
            >
              <Users size={19} />
            </button>
          )}

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

      {user.is_admin && (
        <AdminUserPanel
          currentUser={user}
          open={adminPanelOpen}
          onClose={() => setAdminPanelOpen(false)}
        />
      )}
    </>
  );
}


export default AppHeader;
