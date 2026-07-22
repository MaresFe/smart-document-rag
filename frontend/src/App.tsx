import { useEffect, useState } from "react";

import "./App.css";

import AppHeader from "./components/AppHeader";
import ChatWorkspace from "./components/ChatWorkspace";
import SourceInspector from "./components/SourceInspector";
import SourceSidebar from "./components/SourceSidebar";
import UploadModal from "./components/UploadModal";

type Theme = "light" | "dark";

function getInitialTheme(): Theme {
  const storedTheme = localStorage.getItem("smart-rag-theme");

  if (storedTheme === "light" || storedTheme === "dark") {
    return storedTheme;
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function App() {
  const [theme, setTheme] = useState<Theme>(getInitialTheme);
  const [sourcePanelOpen, setSourcePanelOpen] = useState(true);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);

  const dark = theme === "dark";

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("smart-rag-theme", theme);
  }, [theme]);

  function toggleTheme() {
    setTheme((currentTheme) =>
      currentTheme === "dark" ? "light" : "dark",
    );
  }

  return (
    <div className="application-shell">
      <AppHeader
        dark={dark}
        sourcePanelOpen={sourcePanelOpen}
        onThemeToggle={toggleTheme}
        onSourcePanelToggle={() =>
          setSourcePanelOpen((currentValue) => !currentValue)
        }
      />

      <div
        className={`workspace-layout ${
          sourcePanelOpen ? "" : "source-panel-hidden"
        }`}
      >
        <aside className="source-sidebar">
          <SourceSidebar
            onUploadClick={() => setUploadModalOpen(true)}
          />
        </aside>

        <main className="chat-workspace">
          <ChatWorkspace />
        </main>

        {sourcePanelOpen && (
          <aside className="source-inspector">
            <SourceInspector />
          </aside>
        )}
      </div>

      <UploadModal
        open={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
      />
    </div>
  );
}

export default App;