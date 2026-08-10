import {
  Check,
  Copy,
  RefreshCw,
  Search,
  UserPlus,
  X,
} from "lucide-react";
import {
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from "react";

import type { UserRead } from "../types";
import {
  createUserInvitation,
  getAdminErrorMessage,
  getAdminUsers,
  updateAdminUserStatus,
  type AdminUserRead,
  type InvitationRead,
} from "../services/adminApi";

import "./AdminUserPanel.css";


interface AdminUserPanelProps {
  currentUser: UserRead;
  open: boolean;
  onClose: () => void;
}


function formatDate(value: string): string {
  return new Intl.DateTimeFormat("tr-TR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}


function AdminUserPanel({
  currentUser,
  open,
  onClose,
}: AdminUserPanelProps) {
  const [users, setUsers] = useState<AdminUserRead[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [invitationEmail, setInvitationEmail] = useState("");
  const [inviting, setInviting] = useState(false);
  const [invitation, setInvitation] =
    useState<InvitationRead | null>(null);
  const [copied, setCopied] = useState(false);
  const [confirmationUserId, setConfirmationUserId] =
    useState<string | null>(null);
  const [changingUserId, setChangingUserId] =
    useState<string | null>(null);

  async function loadUsers() {
    setLoading(true);
    setError(null);

    try {
      setUsers(await getAdminUsers());
    } catch (requestError) {
      setError(getAdminErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!open) {
      return;
    }

    void loadUsers();
  }, [open]);

  useEffect(() => {
    if (!open) {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    document.body.classList.add("admin-panel-open");

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.classList.remove("admin-panel-open");
    };
  }, [onClose, open]);

  const filteredUsers = useMemo(() => {
    const normalizedQuery = searchQuery
      .trim()
      .toLocaleLowerCase("tr-TR");

    if (!normalizedQuery) {
      return users;
    }

    return users.filter((user) => {
      const searchableValue = [
        user.full_name ?? "",
        user.email,
      ]
        .join(" ")
        .toLocaleLowerCase("tr-TR");

      return searchableValue.includes(normalizedQuery);
    });
  }, [searchQuery, users]);

  async function handleInvitationSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    const normalizedEmail = invitationEmail
      .trim()
      .toLowerCase();

    if (!normalizedEmail) {
      setError("Davet edilecek e-posta adresini girin.");
      return;
    }

    setInviting(true);
    setError(null);
    setInvitation(null);
    setCopied(false);

    try {
      const createdInvitation =
        await createUserInvitation(normalizedEmail);

      setInvitation(createdInvitation);
      setInvitationEmail("");
    } catch (requestError) {
      setError(getAdminErrorMessage(requestError));
    } finally {
      setInviting(false);
    }
  }

  async function handleStatusChange(user: AdminUserRead) {
    setChangingUserId(user.id);
    setError(null);

    try {
      const updatedUser = await updateAdminUserStatus(
        user.id,
        !user.is_active,
      );

      setUsers((currentUsers) =>
        currentUsers.map((currentUserItem) =>
          currentUserItem.id === updatedUser.id
            ? updatedUser
            : currentUserItem,
        ),
      );
      setConfirmationUserId(null);
    } catch (requestError) {
      setError(getAdminErrorMessage(requestError));
    } finally {
      setChangingUserId(null);
    }
  }

  async function copyInvitationUrl() {
    if (!invitation?.invitation_url) {
      return;
    }

    try {
      await navigator.clipboard.writeText(
        invitation.invitation_url,
      );
      setCopied(true);
    } catch {
      setError("Davet bağlantısı panoya kopyalanamadı.");
    }
  }

  if (!open) {
    return null;
  }

  return (
    <div
      className="admin-panel-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <section
        className="admin-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="admin-panel-title"
      >
        <header className="admin-panel-header">
          <div>
            <p>Yönetim</p>
            <h2 id="admin-panel-title">
              Kullanıcı yönetimi
            </h2>
          </div>

          <button
            className="admin-panel-close"
            type="button"
            aria-label="Yönetim panelini kapat"
            onClick={onClose}
          >
            <X size={18} />
          </button>
        </header>

        <div className="admin-panel-content">
          <section className="admin-invitation-card">
            <div className="admin-section-heading">
              <div className="admin-section-icon">
                <UserPlus size={18} />
              </div>
              <div>
                <h3>Kullanıcı davet et</h3>
                <p>
                  E-posta adresine tek kullanımlık hesap
                  kurulum bağlantısı gönderin.
                </p>
              </div>
            </div>

            <form
              className="admin-invitation-form"
              onSubmit={(event) => {
                void handleInvitationSubmit(event);
              }}
            >
              <input
                type="email"
                name="invitation-email"
                autoComplete="email"
                placeholder="kullanici@sirket.com"
                value={invitationEmail}
                disabled={inviting}
                onChange={(event) =>
                  setInvitationEmail(event.target.value)
                }
              />
              <button type="submit" disabled={inviting}>
                {inviting ? "Gönderiliyor..." : "Davet gönder"}
              </button>
            </form>

            {invitation && (
              <div
                className="admin-invitation-success"
                role="status"
              >
                <div>
                  <strong>Davet oluşturuldu</strong>
                  <span>{invitation.email}</span>
                </div>

                {invitation.invitation_url && (
                  <button
                    type="button"
                    onClick={() => {
                      void copyInvitationUrl();
                    }}
                  >
                    {copied ? (
                      <Check size={15} />
                    ) : (
                      <Copy size={15} />
                    )}
                    {copied ? "Kopyalandı" : "Bağlantıyı kopyala"}
                  </button>
                )}
              </div>
            )}
          </section>

          {error && (
            <div className="admin-panel-error" role="alert">
              {error}
            </div>
          )}

          <section className="admin-users-section">
            <div className="admin-users-toolbar">
              <div>
                <h3>Kullanıcılar</h3>
                <p>{users.length} hesap</p>
              </div>

              <div className="admin-users-actions">
                <label className="admin-user-search">
                  <Search size={15} />
                  <input
                    type="search"
                    placeholder="Kullanıcı ara"
                    value={searchQuery}
                    onChange={(event) =>
                      setSearchQuery(event.target.value)
                    }
                  />
                </label>

                <button
                  className="admin-refresh-button"
                  type="button"
                  aria-label="Kullanıcı listesini yenile"
                  title="Yenile"
                  disabled={loading}
                  onClick={() => {
                    void loadUsers();
                  }}
                >
                  <RefreshCw
                    size={16}
                    className={loading ? "admin-spin" : ""}
                  />
                </button>
              </div>
            </div>

            {loading && users.length === 0 ? (
              <div className="admin-users-state">
                Kullanıcılar yükleniyor...
              </div>
            ) : filteredUsers.length === 0 ? (
              <div className="admin-users-state">
                Eşleşen kullanıcı bulunamadı.
              </div>
            ) : (
              <div className="admin-user-list">
                {filteredUsers.map((user) => {
                  const isCurrentUser =
                    user.id === currentUser.id;
                  const confirmationVisible =
                    confirmationUserId === user.id;
                  const changing = changingUserId === user.id;

                  return (
                    <article
                      className="admin-user-row"
                      key={user.id}
                    >
                      <div className="admin-user-avatar">
                        {(user.full_name ?? user.email)
                          .trim()
                          .charAt(0)
                          .toLocaleUpperCase("tr-TR")}
                      </div>

                      <div className="admin-user-identity">
                        <div>
                          <strong>
                            {user.full_name?.trim() || user.email}
                          </strong>
                          {user.is_admin && (
                            <span className="admin-role-badge">
                              Yönetici
                            </span>
                          )}
                        </div>
                        <span>{user.email}</span>
                      </div>

                      <div className="admin-user-meta">
                        <span
                          className={
                            user.is_active
                              ? "admin-status-active"
                              : "admin-status-inactive"
                          }
                        >
                          {user.is_active ? "Aktif" : "Pasif"}
                        </span>
                        <small>
                          {formatDate(user.created_at)}
                        </small>
                      </div>

                      <div className="admin-user-controls">
                        {isCurrentUser ? (
                          <span>Mevcut hesap</span>
                        ) : user.is_admin ? (
                          <span>Korumalı hesap</span>
                        ) : confirmationVisible ? (
                          <div className="admin-user-confirmation">
                            <button
                              type="button"
                              disabled={changing}
                              onClick={() => {
                                void handleStatusChange(user);
                              }}
                            >
                              {changing ? "İşleniyor..." : "Onayla"}
                            </button>
                            <button
                              type="button"
                              disabled={changing}
                              onClick={() =>
                                setConfirmationUserId(null)
                              }
                            >
                              Vazgeç
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            className={
                              user.is_active
                                ? "admin-deactivate-button"
                                : "admin-activate-button"
                            }
                            onClick={() =>
                              setConfirmationUserId(user.id)
                            }
                          >
                            {user.is_active
                              ? "Pasifleştir"
                              : "Etkinleştir"}
                          </button>
                        )}
                      </div>
                    </article>
                  );
                })}
              </div>
            )}
          </section>
        </div>
      </section>
    </div>
  );
}


export default AdminUserPanel;
