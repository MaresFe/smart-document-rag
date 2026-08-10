import {
  useEffect,
  useState,
  type FormEvent,
} from "react";

import {
  getPasswordResetErrorMessage,
  requestPasswordReset,
} from "../services/passwordResetApi";

import ThemeToggle from "./ThemeToggle";

import "./PasswordResetScreen.css";


interface ForgotPasswordScreenProps {
  initialDark: boolean;
}


function ForgotPasswordScreen({
  initialDark,
}: ForgotPasswordScreenProps) {
  const [dark, setDark] = useState(initialDark);
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [succeeded, setSucceeded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const theme = dark ? "dark" : "light";

    document.documentElement.dataset.theme = theme;
    localStorage.setItem("smart-rag-theme", theme);
  }, [dark]);

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    const normalizedEmail = email.trim().toLowerCase();

    if (!normalizedEmail) {
      setError("E-posta adresini gir.");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      await requestPasswordReset(normalizedEmail);
      setSucceeded(true);
    } catch (requestError) {
      setError(
        getPasswordResetErrorMessage(requestError),
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-screen password-reset-screen">
      <div className="auth-theme-control">
        <ThemeToggle
          dark={dark}
          onToggle={() => setDark((current) => !current)}
        />
      </div>

      <section className="auth-card password-reset-card">
        <div className="auth-brand-panel">
          <img
            className="auth-brand-logo"
            src="/brand/mobilisim-logo.png"
            alt="Mobilişim İletişim A.Ş."
          />

          <div className="auth-brand-copy">
            <p className="auth-product-label">
              Güvenli hesap erişimi
            </p>

            <h1>Hesabınıza yeniden erişin.</h1>

            <p>
              Parola yenileme bağlantıları süreli, tek
              kullanımlık ve yalnızca hesabınıza gönderilir.
            </p>
          </div>

          <p className="auth-privacy-note">
            Hesap bilgileri üçüncü kişilerle paylaşılmaz.
          </p>
        </div>

        <div className="auth-form-panel">
          <div className="auth-form-heading">
            <p className="auth-form-eyebrow">
              Parola yardımı
            </p>

            <h2>Parolanızı yenileyin</h2>

            <p>
              Hesabınızda kullandığınız e-posta adresini
              girin.
            </p>
          </div>

          {succeeded ? (
            <div
              className="password-reset-success"
              role="status"
            >
              <strong>İsteğiniz alındı.</strong>
              <span>
                Bu adresle kullanılabilir bir hesap varsa
                parola yenileme bağlantısı gönderildi.
              </span>
              <a
                className="password-reset-login-link"
                href="/"
              >
                Giriş ekranına dön
              </a>
            </div>
          ) : (
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

              <p className="password-reset-note">
                Güvenlik nedeniyle hesabın sistemde bulunup
                bulunmadığı açıklanmaz.
              </p>

              {error && (
                <div className="auth-error" role="alert">
                  {error}
                </div>
              )}

              <button
                className="auth-submit-button"
                type="submit"
                disabled={submitting}
              >
                {submitting
                  ? "İstek gönderiliyor..."
                  : "Yenileme bağlantısı gönder"}
              </button>

              <a
                className="password-reset-login-link"
                href="/"
              >
                Giriş ekranına dön
              </a>
            </form>
          )}
        </div>
      </section>
    </main>
  );
}


export default ForgotPasswordScreen;
