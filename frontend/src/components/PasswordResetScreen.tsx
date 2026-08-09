import {
  useEffect,
  useState,
  type FormEvent,
} from "react";

import {
  confirmPasswordReset,
  getPasswordResetErrorMessage,
  previewPasswordReset,
} from "../services/passwordResetApi";

import ThemeToggle from "./ThemeToggle";

import "./PasswordResetScreen.css";


interface PasswordResetScreenProps {
  token: string | null;
  initialDark: boolean;
}


function PasswordResetScreen({
  token,
  initialDark,
}: PasswordResetScreenProps) {
  const [dark, setDark] = useState(initialDark);
  const [password, setPassword] = useState("");
  const [passwordConfirmation, setPasswordConfirmation] =
    useState("");
  const [previewLoading, setPreviewLoading] = useState(
    token !== null,
  );
  const [tokenIsValid, setTokenIsValid] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [succeeded, setSucceeded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const theme = dark ? "dark" : "light";

    document.documentElement.dataset.theme = theme;
    localStorage.setItem("smart-rag-theme", theme);
  }, [dark]);

  useEffect(() => {
    let active = true;

    async function validateToken() {
      if (!token) {
        setPreviewLoading(false);
        return;
      }

      setPreviewLoading(true);
      setError(null);

      try {
        await previewPasswordReset(token);

        if (active) {
          setTokenIsValid(true);
        }
      } catch (requestError) {
        if (active) {
          setTokenIsValid(false);
          setError(
            getPasswordResetErrorMessage(requestError),
          );
        }
      } finally {
        if (active) {
          setPreviewLoading(false);
        }
      }
    }

    void validateToken();

    return () => {
      active = false;
    };
  }, [token]);

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (!token || !tokenIsValid) {
      setError(
        "Geçerli bir parola yenileme bağlantısı bulunamadı.",
      );
      return;
    }

    if (password.length < 10) {
      setError("Parola en az 10 karakter olmalıdır.");
      return;
    }

    if (password !== passwordConfirmation) {
      setError("Parolalar birbiriyle eşleşmiyor.");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      await confirmPasswordReset(token, password);
      setSucceeded(true);

      window.setTimeout(() => {
        window.location.replace("/");
      }, 1200);
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
              Güvenli parola yenileme
            </p>

            <h1>Yeni parolanızı belirleyin.</h1>

            <p>
              Bu bağlantı süreli ve tek kullanımlıktır.
              Tamamlandığında yeniden giriş yapmanız gerekir.
            </p>
          </div>

          <p className="auth-privacy-note">
            Güçlü ve başka hesaplarda kullanmadığınız bir
            parola seçin.
          </p>
        </div>

        <div className="auth-form-panel">
          <div className="auth-form-heading">
            <p className="auth-form-eyebrow">
              Hesap güvenliği
            </p>

            <h2>Parolayı değiştir</h2>

            <p>
              Hesabınız için en az 10 karakter uzunluğunda
              yeni bir parola oluşturun.
            </p>
          </div>

          {!token ? (
            <div className="password-reset-invalid" role="alert">
              <p>
                Parola yenileme bağlantısında geçerli bir
                token bulunamadı.
              </p>
              <a href="/forgot-password">
                Yeni bağlantı iste
              </a>
            </div>
          ) : previewLoading ? (
            <div
              className="password-reset-loading"
              role="status"
            >
              Parola yenileme bağlantısı doğrulanıyor...
            </div>
          ) : !tokenIsValid ? (
            <div className="password-reset-invalid" role="alert">
              <p>
                {error
                  ?? "Parola yenileme bağlantısı doğrulanamadı."}
              </p>
              <a href="/forgot-password">
                Yeni bağlantı iste
              </a>
            </div>
          ) : succeeded ? (
            <div
              className="password-reset-success"
              role="status"
            >
              <strong>Parolanız değiştirildi.</strong>
              <span>
                Giriş ekranına yönlendiriliyorsunuz.
              </span>
            </div>
          ) : (
            <form
              className="auth-form"
              onSubmit={(event) => {
                void handleSubmit(event);
              }}
            >
              <label className="auth-field">
                <span>Yeni parola</span>

                <input
                  type="password"
                  name="password"
                  autoComplete="new-password"
                  placeholder="En az 10 karakter"
                  value={password}
                  disabled={submitting}
                  onChange={(event) =>
                    setPassword(event.target.value)
                  }
                />
              </label>

              <label className="auth-field">
                <span>Yeni parolayı doğrula</span>

                <input
                  type="password"
                  name="password-confirmation"
                  autoComplete="new-password"
                  placeholder="Yeni parolanızı tekrar girin"
                  value={passwordConfirmation}
                  disabled={submitting}
                  onChange={(event) =>
                    setPasswordConfirmation(event.target.value)
                  }
                />
              </label>

              <p className="password-reset-note">
                En az 10 karakter kullanın; tahmin edilmesi
                kolay veya başka hesaplarda kullandığınız bir
                parola seçmeyin.
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
                  ? "Parola değiştiriliyor..."
                  : "Parolayı değiştir"}
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


export default PasswordResetScreen;

