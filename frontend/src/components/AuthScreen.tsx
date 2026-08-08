import {
  useState,
  type FormEvent,
} from "react";

import type {
  UserLoginCreate,
  UserRegisterCreate,
} from "../types";

import ThemeToggle from "./ThemeToggle";


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
  onClearError,
  onThemeToggle,
}: AuthScreenProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [formError, setFormError] =
    useState<string | null>(null);

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    const normalizedEmail = email.trim().toLowerCase();

    if (!normalizedEmail) {
      setFormError("E-posta adresini gir.");
      return;
    }

    if (!password) {
      setFormError("Parolanı gir.");
      return;
    }

    setFormError(null);
    onClearError();

    await onLogin({
      email: normalizedEmail,
      password,
    });
  }

  const visibleError = formError ?? error;

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
              Belgelerinize güvenli şekilde erişin.
            </h1>

            <p>
              Belgeleriniz, sohbetleriniz ve kaynaklarınız
              yalnızca size ait çalışma alanında saklanır.
            </p>
          </div>

          <p className="auth-privacy-note">
            Her kullanıcı için ayrı ve korumalı çalışma alanı.
          </p>
        </div>

        <div className="auth-form-panel">
          <div className="auth-form-heading">
            <p className="auth-form-eyebrow">
              Hesabınız
            </p>

            <h2>Giriş yap</h2>

            <p>
              Belgelerinize ve sohbetlerinize devam edin.
            </p>
          </div>

          <form
            className="auth-form"
            onSubmit={(event) => {
              void handleSubmit(event);
            }}
          >
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
                  setEmail(event.target.value)
                }
              />
            </label>

            <label className="auth-field">
              <span>Parola</span>

              <input
                type="password"
                name="password"
                autoComplete="current-password"
                placeholder="Parolanız"
                value={password}
                disabled={submitting}
                onChange={(event) =>
                  setPassword(event.target.value)
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
                ? "Giriş yapılıyor..."
                : "Giriş yap"}
            </button>
          </form>

          <p className="auth-switch-copy">
            Yeni hesaplar yalnızca yönetici davetiyle
            oluşturulur.
          </p>
        </div>
      </section>
    </main>
  );
}


export default AuthScreen;
