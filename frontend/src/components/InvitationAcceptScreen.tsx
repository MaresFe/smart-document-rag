import {
  useEffect,
  useState,
  type FormEvent,
} from "react";

import {
  acceptInvitation,
  getInvitationErrorMessage,
  getInvitationPreview,
  type InvitationPreview,
} from "../services/invitationApi";

import ThemeToggle from "./ThemeToggle";

import "./InvitationAcceptScreen.css";


interface InvitationAcceptScreenProps {
  token: string | null;
  initialDark: boolean;
}


function InvitationAcceptScreen({
  token,
  initialDark,
}: InvitationAcceptScreenProps) {
  const [dark, setDark] = useState(initialDark);
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirmation, setPasswordConfirmation] =
    useState("");
  const [submitting, setSubmitting] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(
    token !== null,
  );
  const [preview, setPreview] =
    useState<InvitationPreview | null>(null);
  const [succeeded, setSucceeded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const theme = dark ? "dark" : "light";

    document.documentElement.dataset.theme = theme;
    localStorage.setItem("smart-rag-theme", theme);
  }, [dark]);

  useEffect(() => {
    let active = true;

    async function loadInvitationPreview() {
      if (!token) {
        setPreviewLoading(false);
        return;
      }

      setPreviewLoading(true);
      setError(null);

      try {
        const invitationPreview =
          await getInvitationPreview(token);

        if (active) {
          setPreview(invitationPreview);
        }
      } catch (requestError) {
        if (active) {
          setPreview(null);
          setError(
            getInvitationErrorMessage(requestError),
          );
        }
      } finally {
        if (active) {
          setPreviewLoading(false);
        }
      }
    }

    void loadInvitationPreview();

    return () => {
      active = false;
    };
  }, [token]);

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (!token || !preview) {
      setError("Geçerli bir davet bağlantısı bulunamadı.");
      return;
    }

    const normalizedFullName = fullName
      .trim()
      .replace(/\s+/g, " ");

    if (normalizedFullName.length < 2) {
      setError("Ad ve soyad alanını doldur.");
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
      await acceptInvitation({
        token,
        password,
        full_name: normalizedFullName,
      });

      setSucceeded(true);

      window.setTimeout(() => {
        window.location.replace("/");
      }, 700);

    } catch (requestError) {
      setError(
        getInvitationErrorMessage(requestError),
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-screen invitation-screen">
      <div className="auth-theme-control">
        <ThemeToggle
          dark={dark}
          onToggle={() => setDark((current) => !current)}
        />
      </div>

      <section className="auth-card invitation-card">
        <div className="auth-brand-panel">
          <img
            className="auth-brand-logo"
            src="/brand/mobilisim-logo.png"
            alt="Mobilişim İletişim A.Ş."
          />

          <div className="auth-brand-copy">
            <p className="auth-product-label">
              Güvenli davet
            </p>

            <h1>Çalışma alanınızı oluşturun.</h1>

            <p>
              Bu bağlantı yalnızca davet edilen hesap için
              ve tek kullanımlık olarak hazırlanmıştır.
            </p>
          </div>

          <p className="auth-privacy-note">
            Davet bağlantıları süreli ve tek kullanımlıktır.
          </p>
        </div>

        <div className="auth-form-panel">
          <div className="auth-form-heading">
            <p className="auth-form-eyebrow">
              Hesap kurulumu
            </p>

            <h2>Davetinizi kabul edin</h2>

            <p>
              Adınızı ve güvenli parolanızı belirleyerek
              hesabınızı etkinleştirin.
            </p>
          </div>

          {!token ? (
            <div className="invitation-invalid" role="alert">
              <p>
                Geçerli bir davet tokenı bulunamadı. Bağlantı
                eksik veya daha önce temizlenmiş olabilir.
              </p>

              <a href="/">Giriş ekranına dön</a>
            </div>
          ) : previewLoading ? (
            <div
              className="invitation-loading"
              role="status"
            >
              Davet bilgileri doğrulanıyor...
            </div>
          ) : !preview ? (
            <div className="invitation-invalid" role="alert">
              <p>
                {error ?? "Davet bağlantısı doğrulanamadı."}
              </p>

              <a href="/">Giriş ekranına dön</a>
            </div>
          ) : succeeded ? (
            <div
              className="invitation-success"
              role="status"
            >
              <strong>Hesabınız oluşturuldu.</strong>
              <span>Çalışma alanına yönlendiriliyorsunuz.</span>
            </div>
          ) : (
            <form
              className="auth-form"
              onSubmit={(event) => {
                void handleSubmit(event);
              }}
            >
              <label className="auth-field">
                <span>Davet edilen e-posta</span>

                <input
                  className="invitation-email-input"
                  type="email"
                  value={preview.email}
                  readOnly
                  aria-readonly="true"
                />
              </label>

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
                    setFullName(event.target.value)
                  }
                />
              </label>

              <label className="auth-field">
                <span>Parola</span>

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
                <span>Parolayı doğrula</span>

                <input
                  type="password"
                  name="password-confirmation"
                  autoComplete="new-password"
                  placeholder="Parolanızı tekrar girin"
                  value={passwordConfirmation}
                  disabled={submitting}
                  onChange={(event) =>
                    setPasswordConfirmation(event.target.value)
                  }
                />
              </label>

              <p className="invitation-password-note">
                En az 10 karakter uzunluğunda bir parola kullanın.
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
                  ? "Hesap oluşturuluyor..."
                  : "Daveti kabul et"}
              </button>

              <a
                className="invitation-login-link"
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


export default InvitationAcceptScreen;
