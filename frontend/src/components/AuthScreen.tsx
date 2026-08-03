import {
  useState,
  type FormEvent,
} from "react";

import type {
  UserLoginCreate,
  UserRegisterCreate,
} from "../types";

import ThemeToggle from "./ThemeToggle";

type AuthMode = "login" | "register";

interface AuthScreenProps {
  dark: boolean;
  submitting: boolean;
  error: string | null;
  onLogin: (
    credentials: UserLoginCreate,
  ) => Promise<void>;
  onRegister: (
    registration: UserRegisterCreate,
  ) => Promise<void>;
  onClearError: () => void;
  onThemeToggle: () => void;
}

function AuthScreen({
  dark,
  submitting,
  error,
  onLogin,
  onRegister,
  onClearError,
  onThemeToggle,
}: AuthScreenProps) {
  const [mode, setMode] =
    useState<AuthMode>("login");

  const [fullName, setFullName] =
    useState("");

  const [email, setEmail] =
    useState("");

  const [password, setPassword] =
    useState("");

  const [formError, setFormError] =
    useState<string | null>(null);

  const registering = mode === "register";

  function changeMode(nextMode: AuthMode) {
    if (submitting) {
      return;
    }

    setMode(nextMode);
    setPassword("");
    setFormError(null);
    onClearError();
  }

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    const normalizedEmail =
      email.trim().toLowerCase();

    const normalizedFullName =
      fullName.trim();

    if (!normalizedEmail) {
      setFormError(
        "E-posta adresini gir.",
      );
      return;
    }

    if (
      registering &&
      !normalizedFullName
    ) {
      setFormError(
        "Ad ve soyad alanını doldur.",
      );
      return;
    }

    if (password.length < 8) {
      setFormError(
        "Parola en az 8 karakter olmalıdır.",
      );
      return;
    }

    setFormError(null);
    onClearError();

    if (registering) {
      await onRegister({
        email: normalizedEmail,
        password,
        full_name: normalizedFullName,
      });

      return;
    }

    await onLogin({
      email: normalizedEmail,
      password,
    });
  }

  const visibleError =
    formError ?? error;

  return (
    <main className="auth-screen">
      <div className="auth-theme-control">
  <ThemeToggle
    dark={dark}
    onToggle={onThemeToggle}
  />
</div>
      <section className="auth-card">
        <div className="auth-brand-panel">
          <img
            className="auth-brand-logo"
            src="/brand/mobilisim-logo.png"
            alt="Mobilişim İletişim A.Ş."
          />

          <div className="auth-brand-copy">
            <p className="auth-product-label">
              Belge Asistanı
            </p>

            <h1>
              Belgelerinize güvenli şekilde
              erişin.
            </h1>

            <p>
              Belgeleriniz, sohbetleriniz ve
              kaynaklarınız yalnızca size ait
              çalışma alanında saklanır.
            </p>
          </div>

          <p className="auth-privacy-note">
            Her kullanıcı için ayrı ve korumalı
            çalışma alanı.
          </p>
        </div>

        <div className="auth-form-panel">
          <div className="auth-form-heading">
            <p className="auth-form-eyebrow">
              {registering
                ? "Yeni hesap"
                : "Hesabınız"}
            </p>

            <h2>
              {registering
                ? "Hesap oluştur"
                : "Giriş yap"}
            </h2>

            <p>
              {registering
                ? "Kişisel belge çalışma alanınızı oluşturun."
                : "Belgelerinize ve sohbetlerinize devam edin."}
            </p>
          </div>

          <div
            className="auth-mode-switch"
            role="tablist"
            aria-label="Hesap işlemi"
          >
            <button
              className={
                mode === "login"
                  ? "auth-mode-active"
                  : ""
              }
              type="button"
              role="tab"
              aria-selected={
                mode === "login"
              }
              disabled={submitting}
              onClick={() =>
                changeMode("login")
              }
            >
              Giriş
            </button>

            <button
              className={
                mode === "register"
                  ? "auth-mode-active"
                  : ""
              }
              type="button"
              role="tab"
              aria-selected={
                mode === "register"
              }
              disabled={submitting}
              onClick={() =>
                changeMode("register")
              }
            >
              Kayıt
            </button>
          </div>

          <form
            className="auth-form"
            onSubmit={(event) => {
              void handleSubmit(event);
            }}
          >
            {registering && (
              <label className="auth-field">
                <span>Ad ve soyad</span>

                <input
                  type="text"
                  name="name"
                  autoComplete="name"
                  placeholder="Adınız ve soyadınız"
                  value={fullName}
                  disabled={submitting}
                  onChange={(event) =>
                    setFullName(
                      event.target.value,
                    )
                  }
                />
              </label>
            )}

            <label className="auth-field">
              <span>E-posta</span>

              <input
                type="email"
                name="email"
                autoComplete="email"
                placeholder="ornek@eposta.com"
                value={email}
                disabled={submitting}
                onChange={(event) =>
                  setEmail(
                    event.target.value,
                  )
                }
              />
            </label>

            <label className="auth-field">
              <span>Parola</span>

              <input
                type="password"
                name="password"
                autoComplete={
                  registering
                    ? "new-password"
                    : "current-password"
                }
                placeholder="En az 8 karakter"
                value={password}
                disabled={submitting}
                onChange={(event) =>
                  setPassword(
                    event.target.value,
                  )
                }
              />
            </label>

            {visibleError && (
              <div
                className="auth-error"
                role="alert"
              >
                {visibleError}
              </div>
            )}

            <button
              className="auth-submit-button"
              type="submit"
              disabled={submitting}
            >
              {submitting
                ? "İşlem sürüyor..."
                : registering
                  ? "Hesap oluştur"
                  : "Giriş yap"}
            </button>
          </form>

          <p className="auth-switch-copy">
            {registering
              ? "Zaten hesabınız var mı?"
              : "Henüz hesabınız yok mu?"}

            <button
              type="button"
              disabled={submitting}
              onClick={() =>
                changeMode(
                  registering
                    ? "login"
                    : "register",
                )
              }
            >
              {registering
                ? "Giriş yapın"
                : "Hesap oluşturun"}
            </button>
          </p>
        </div>
      </section>
    </main>
  );
}

export default AuthScreen;