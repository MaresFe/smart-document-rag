import { useRef, useState } from "react";

import {
  FileText,
  UploadCloud,
  X,
} from "lucide-react";

interface UploadModalProps {
  open: boolean;
  onClose: () => void;
}

function UploadModal({
  open,
  onClose,
}: UploadModalProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);

  if (!open) {
    return null;
  }

  function addFiles(files: FileList | null) {
    if (!files) {
      return;
    }

    const incomingFiles = Array.from(files);

    setSelectedFiles((currentFiles) => {
      const knownFiles = new Set(
        currentFiles.map(
          (file) => `${file.name}-${file.size}`,
        ),
      );

      const uniqueIncomingFiles = incomingFiles.filter(
        (file) =>
          !knownFiles.has(`${file.name}-${file.size}`),
      );

      return [...currentFiles, ...uniqueIncomingFiles];
    });
  }

  function closeModal() {
    setDragging(false);
    setSelectedFiles([]);
    onClose();
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
            setDragging(true);
          }}
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
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
            <UploadCloud size={34} />
          </div>

          <h3>Dosyaları buraya bırak</h3>

          <p>
            PDF, DOCX, TXT, CSV ve XLSX dosyaları
            desteklenir.
          </p>

          <input
            ref={inputRef}
            type="file"
            multiple
            hidden
            accept=".pdf,.docx,.txt,.csv,.xlsx"
            onChange={(event) =>
              addFiles(event.target.files)
            }
          />

          <button
            className="secondary-btn upload-select-button"
            type="button"
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
                key={`${file.name}-${file.size}`}
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
                  aria-label={`${file.name} dosyasını kaldır`}
                  onClick={() =>
                    setSelectedFiles((currentFiles) =>
                      currentFiles.filter(
                        (currentFile) =>
                          currentFile !== file,
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

        <div className="modal-actions">
          <button
            className="secondary-btn"
            type="button"
            onClick={closeModal}
          >
            İptal
          </button>

          <button
            className="primary-btn"
            type="button"
            disabled={selectedFiles.length === 0}
          >
            {selectedFiles.length > 0
              ? `${selectedFiles.length} dosyayı yükle`
              : "Dosya seçin"}
          </button>
        </div>
      </section>
    </div>
  );
}

export default UploadModal;