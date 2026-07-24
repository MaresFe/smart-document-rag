import { useEffect, useRef, useState } from "react";

import {
  FileText,
  LoaderCircle,
  UploadCloud,
  X,
} from "lucide-react";

interface UploadModalProps {
  open: boolean;
  onClose: () => void;
  onUpload: (files: File[]) => Promise<void>;
}

function UploadModal({
  open,
  onClose,
  onUpload,
}: UploadModalProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const [dragging, setDragging] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      setDragging(false);
      setSelectedFiles([]);
      setUploading(false);
      setUploadError(null);
    }
  }, [open]);

  if (!open) {
    return null;
  }

  function addFiles(files: FileList | null) {
    if (!files || uploading) {
      return;
    }

    const incomingFiles = Array.from(files);

    setSelectedFiles((currentFiles) => {
      const knownFiles = new Set(
        currentFiles.map(
          (file) => `${file.name}-${file.size}-${file.lastModified}`,
        ),
      );

      const uniqueIncomingFiles = incomingFiles.filter(
        (file) =>
          !knownFiles.has(
            `${file.name}-${file.size}-${file.lastModified}`,
          ),
      );

      return [...currentFiles, ...uniqueIncomingFiles];
    });

    setUploadError(null);

    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }

  function closeModal() {
    if (uploading) {
      return;
    }

    setDragging(false);
    setSelectedFiles([]);
    setUploadError(null);
    onClose();
  }

  async function submitUpload() {
    if (selectedFiles.length === 0 || uploading) {
      return;
    }

    setUploading(true);
    setUploadError(null);

    try {
      await onUpload(selectedFiles);
      closeModal();
    } catch (error) {
      setUploadError(
        error instanceof Error
          ? error.message
          : "Dosyalar yüklenemedi.",
      );
    } finally {
      setUploading(false);
    }
  }

  return (
    <div
      className="modal-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          closeModal();
        }
      }}
    >
      <section
        className="upload-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="upload-modal-title"
      >
        <div className="modal-header">
          <div>
            <p className="eyebrow">Yeni Kaynak</p>
            <h2 id="upload-modal-title">Doküman yükle</h2>
          </div>

          <button
            type="button"
            aria-label="Pencereyi kapat"
            disabled={uploading}
            onClick={closeModal}
          >
            <X size={18} />
          </button>
        </div>

        <div
          className={`dropzone ${
            dragging ? "dropzone-active" : ""
          }`}
          onDragEnter={(event) => {
            event.preventDefault();

            if (!uploading) {
              setDragging(true);
            }
          }}
          onDragOver={(event) => {
            event.preventDefault();

            if (!uploading) {
              setDragging(true);
            }
          }}
          onDragLeave={(event) => {
            event.preventDefault();
            setDragging(false);
          }}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            addFiles(event.dataTransfer.files);
          }}
        >
          <div className="dropzone-icon">
            {uploading ? (
              <LoaderCircle className="spinning-icon" size={34} />
            ) : (
              <UploadCloud size={34} />
            )}
          </div>

          <h3>
            {uploading
              ? "Dokümanlar işleniyor"
              : "Dosyaları buraya bırak"}
          </h3>

          <p>
            PDF, DOCX ve TXT dosyaları yükleyebilirsin. Yükleme
            sırasında metin çıkarma, chunking ve embedding işlemleri
            uygulanır.
          </p>

          <input
            ref={inputRef}
            type="file"
            multiple
            hidden
            disabled={uploading}
            accept=".pdf,.docx,.txt"
            onChange={(event) => addFiles(event.target.files)}
          />

          <button
            className="secondary-btn upload-select-button"
            type="button"
            disabled={uploading}
            onClick={() => inputRef.current?.click()}
          >
            Dosya seç
          </button>
        </div>

        {selectedFiles.length > 0 && (
          <div className="selected-file-list">
            <div className="selected-file-heading">
              <strong>Seçilen dosyalar</strong>
              <span>{selectedFiles.length} dosya</span>
            </div>

            {selectedFiles.map((file) => (
              <div
                className="selected-file-item"
                key={`${file.name}-${file.size}-${file.lastModified}`}
              >
                <span className="selected-file-icon">
                  <FileText size={17} />
                </span>

                <span className="selected-file-copy">
                  <strong>{file.name}</strong>

                  <span>
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </span>
                </span>

                <button
                  type="button"
                  disabled={uploading}
                  aria-label={`${file.name} dosyasını kaldır`}
                  onClick={() =>
                    setSelectedFiles((currentFiles) =>
                      currentFiles.filter(
                        (currentFile) => currentFile !== file,
                      ),
                    )
                  }
                >
                  <X size={15} />
                </button>
              </div>
            ))}
          </div>
        )}

        {uploadError && (
          <div className="modal-api-error" role="alert">
            {uploadError}
          </div>
        )}

        <div className="modal-actions">
          <button
            className="secondary-btn"
            type="button"
            disabled={uploading}
            onClick={closeModal}
          >
            İptal
          </button>

          <button
            className="primary-btn"
            type="button"
            disabled={selectedFiles.length === 0 || uploading}
            onClick={() => {
              void submitUpload();
            }}
          >
            {uploading ? (
              <>
                <LoaderCircle className="spinning-icon" size={17} />
                İşleniyor
              </>
            ) : selectedFiles.length > 0 ? (
              `${selectedFiles.length} dosyayı yükle`
            ) : (
              "Dosya seçin"
            )}
          </button>
        </div>
      </section>
    </div>
  );
}

export default UploadModal;