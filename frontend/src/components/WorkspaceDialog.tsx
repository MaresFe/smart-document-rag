import {
  type FormEvent,
  useEffect,
  useRef,
  useState,
} from "react";

import { LoaderCircle } from "lucide-react";

export type WorkspaceDialogType =
  | "delete-document"
  | "delete-session"
  | "rename-session";

export interface WorkspaceDialogState {
  type: WorkspaceDialogType;
  targetId: string;
  targetName: string;
}

interface WorkspaceDialogProps {
  dialog: WorkspaceDialogState | null;
  busy: boolean;
  error: string | null;
  onClose: () => void;
  onConfirm: (value: string) => Promise<boolean>;
}

function WorkspaceDialog({
  dialog,
  busy,
  error,
  onClose,
  onConfirm,
}: WorkspaceDialogProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [value, setValue] = useState("");
  const [validationError, setValidationError] =
    useState<string | null>(null);

  const renameMode =
    dialog?.type === "rename-session";

  useEffect(() => {
    if (!dialog) {
      setValue("");
      setValidationError(null);
      return;
    }

    setValue(dialog.targetName);
    setValidationError(null);

    if (dialog.type === "rename-session") {
      requestAnimationFrame(() => {
        inputRef.current?.focus();
        inputRef.current?.select();
      });
    }
  }, [dialog]);

  if (!dialog) {
    return null;
  }

  const title =
    dialog.type === "delete-document"
      ? "Belgeyi sil"
      : dialog.type === "delete-session"
        ? "Sohbeti sil"
        : "Sohbeti yeniden adlandır";

  const description =
    dialog.type === "delete-document"
      ? `"${dialog.targetName}" belgesi kalıcı olarak silinecek.`
      : dialog.type === "delete-session"
        ? `"${dialog.targetName}" sohbeti ve mesaj geçmişi kalıcı olarak silinecek.`
        : "Sohbet listesinde görünecek yeni adı gir.";

  const destructive =
    dialog.type !== "rename-session";

  async function submit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (busy) {
      return;
    }

    const normalizedValue = value.trim();

    if (renameMode && !normalizedValue) {
      setValidationError(
        "Sohbet adı boş bırakılamaz.",
      );
      inputRef.current?.focus();
      return;
    }

    setValidationError(null);

    const completed = await onConfirm(
      normalizedValue,
    );

    if (completed) {
      onClose();
    }
  }

  return (
    <div
      className="modal-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (
          event.target === event.currentTarget &&
          !busy
        ) {
          onClose();
        }
      }}
      onKeyDown={(event) => {
        if (event.key === "Escape" && !busy) {
          onClose();
        }
      }}
    >
      <form
        className="action-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="workspace-dialog-title"
        aria-describedby="workspace-dialog-description"
        onSubmit={(event) => {
          void submit(event);
        }}
      >
        <div className="action-modal-heading">
          <p className="eyebrow">
            {destructive
              ? "Kalıcı işlem"
              : "Sohbet ayarları"}
          </p>

          <h2 id="workspace-dialog-title">
            {title}
          </h2>
        </div>

        <p
          className="action-modal-description"
          id="workspace-dialog-description"
        >
          {description}
        </p>

        {renameMode && (
          <label className="action-modal-field">
            <span>Sohbet adı</span>

            <input
              ref={inputRef}
              value={value}
              maxLength={120}
              disabled={busy}
              autoComplete="off"
              onChange={(event) => {
                setValue(event.target.value);
                setValidationError(null);
              }}
            />
          </label>
        )}

        {(validationError || error) && (
          <div className="modal-api-error" role="alert">
            {validationError || error}
          </div>
        )}

        {destructive && (
          <p className="action-modal-warning">
            Bu işlem geri alınamaz.
          </p>
        )}

        <div className="modal-actions">
          <button
            className="secondary-btn"
            type="button"
            autoFocus={!renameMode}
            disabled={busy}
            onClick={onClose}
          >
            İptal
          </button>

          <button
            className={
              destructive
                ? "danger-btn"
                : "primary-btn"
            }
            type="submit"
            disabled={
              busy ||
              (renameMode && value.trim().length === 0)
            }
          >
            {busy ? (
              <>
                <LoaderCircle
                  className="spinning-icon"
                  size={16}
                />
                İşleniyor
              </>
            ) : destructive ? (
              "Sil"
            ) : (
              "Kaydet"
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

export default WorkspaceDialog;
