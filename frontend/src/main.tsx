import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "./index.css";

import App from "./App.tsx";
import InvitationAcceptScreen from "./components/InvitationAcceptScreen";


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


const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("Root element could not be found.");
}

const normalizedPath =
  window.location.pathname.replace(/\/+$/, "") || "/";
const invitationRoute =
  normalizedPath === "/accept-invitation";
const invitationToken = invitationRoute
  ? new URLSearchParams(window.location.search).get("token")
  : null;
const initialTheme = getInitialTheme();

document.documentElement.dataset.theme = initialTheme;

if (invitationRoute && window.location.search) {
  window.history.replaceState(
    null,
    "",
    "/accept-invitation",
  );
}

createRoot(rootElement).render(
  <StrictMode>
    {invitationRoute ? (
      <InvitationAcceptScreen
        token={invitationToken}
        initialDark={initialTheme === "dark"}
      />
    ) : (
      <App />
    )}
  </StrictMode>,
);
