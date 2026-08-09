import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "./index.css";

import App from "./App.tsx";
import ForgotPasswordScreen from "./components/ForgotPasswordScreen";
import InvitationAcceptScreen from "./components/InvitationAcceptScreen";
import PasswordResetScreen from "./components/PasswordResetScreen";


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
const forgotPasswordRoute =
  normalizedPath === "/forgot-password";
const passwordResetRoute =
  normalizedPath === "/reset-password";
const invitationToken = invitationRoute
  ? new URLSearchParams(window.location.search).get("token")
  : null;
const passwordResetToken = passwordResetRoute
  ? new URLSearchParams(window.location.search).get("token")
  : null;
const initialTheme = getInitialTheme();

document.documentElement.dataset.theme = initialTheme;

if (
  (invitationRoute || passwordResetRoute)
  && window.location.search
) {
  window.history.replaceState(
    null,
    "",
    normalizedPath,
  );
}

createRoot(rootElement).render(
  <StrictMode>
    {invitationRoute ? (
      <InvitationAcceptScreen
        token={invitationToken}
        initialDark={initialTheme === "dark"}
      />
    ) : forgotPasswordRoute ? (
      <ForgotPasswordScreen
        initialDark={initialTheme === "dark"}
      />
    ) : passwordResetRoute ? (
      <PasswordResetScreen
        token={passwordResetToken}
        initialDark={initialTheme === "dark"}
      />
    ) : (
      <App />
    )}
  </StrictMode>,
);
