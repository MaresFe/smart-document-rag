import {
  useEffect,
  useRef,
  useState,
} from "react";

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


function getFileKey(file: File): string {
  return [
    file.name,
    file.size,
    file.lastModified,
  ].join("-");
}


function formatFileSize(size: number): string {
  if (size === 0) {
    return "0 B";
  }

  if (size < 1024) {
    return `${size} B`;
  }

  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }

  return (
    `${(size / 1024 / 1024).toFixed(2)} MB`
  );
}


function getUploadErrorMessage(
  error: unknown,
): string {
  if (
    error instanceof Error
    && error.message.trim()
  ) {
    return error.message;
  }

  return "Dosya yüklenemedi.";
}


function UploadModal({
  open,
  onClose,
  onUpload,
}: UploadModalProps) {
  const inputRef =
    useRef<HTMLInputElement>(null);

  const selectedFileListRef =
    useRef<HTMLDivElement>(null);

  const [
    dragging,
    setDragging,
  ] = useState(false);

  const [
    selectedFiles,
    setSelectedFiles,
  ] = useState<File[]>([]);

  const [
    uploading,
    setUploading,
  ] = useState(false);

  const [
    activeFileKey,
    setActiveFileKey,
  ] = useState<string | null>(null);

  const [
    uploadSummary,
    setUploadSummary,
  ] = useState<string | null>(null);

  const [
    fileErrors,
    setFileErrors,
  ] = useState<Record<string, string>>({});

  const hasFileErrors =
    Object.keys(fileErrors).length > 0;


  useEffect(() => {
    if (!open) {
      setDragging(false);
      setSelectedFiles([]);
      setUploading(false);
      setActiveFileKey(null);
      setUploadSummary(null);
      setFileErrors({});
    }
  }, [open]);


  useEffect(() => {
    if (
      !uploadSummary
      || selectedFiles.length === 0
    ) {
      return;
    }

    requestAnimationFrame(() => {
      selectedFileListRef.current?.scrollTo({
        top: 0,
        behavior: "auto",
      });
    });
  }, [
    uploadSummary,
    selectedFiles.length,
  ]);


  if (!open) {
    return null;
  }


  function addFiles(
    files: FileList | null,
  ) {
    if (!files || uploading) {
      return;
    }

    const incomingFiles =
      Array.from(files);

    setSelectedFiles(
      (currentFiles) => {
        const knownFiles = new Set(
          currentFiles.map(getFileKey),
        );

        const uniqueIncomingFiles =
          incomingFiles.filter(
            (file) =>
              !knownFiles.has(
                getFileKey(file),
              ),
          );

        return [
          ...currentFiles,
          ...uniqueIncomingFiles,
        ];
      },
    );

    setUploadSummary(null);

    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }


  function removeFile(
    fileToRemove: File,
  ) {
    if (uploading) {
      return;
    }

    const fileKey =
      getFileKey(fileToRemove);

    setSelectedFiles(
      (currentFiles) =>
        currentFiles.filter(
          (file) =>
            getFileKey(file) !== fileKey,
        ),
    );

    setFileErrors(
      (currentErrors) => {
        const nextErrors = {
          ...currentErrors,
        };

        delete nextErrors[fileKey];

        return nextErrors;
      },
    );

    setUploadSummary(null);
  }


  function resetModalState() {
    setDragging(false);
    setSelectedFiles([]);
    setUploading(false);
    setActiveFileKey(null);
    setUploadSummary(null);
    setFileErrors({});
  }


  function closeModal() {
    if (uploading) {
      return;
    }

    resetModalState();
    onClose();
  }


  async function submitUpload() {
    if (
      selectedFiles.length === 0
      || uploading
    ) {
      return;
    }

    const filesToUpload = [
      ...selectedFiles,
    ];

    const failedFiles: File[] = [];

    const nextFileErrors:
      Record<string, string> = {};

    let successfulUploadCount = 0;

    setUploading(true);
    setUploadSummary(null);
    setFileErrors({});

    for (const file of filesToUpload) {
      const fileKey = getFileKey(file);

      setActiveFileKey(fileKey);

      try {
        await onUpload([file]);
        successfulUploadCount += 1;

      } catch (error) {
        failedFiles.push(file);

        nextFileErrors[fileKey] =
          getUploadErrorMessage(error);
      }
    }

    setActiveFileKey(null);
    setUploading(false);

    if (failedFiles.length === 0) {
      resetModalState();
      onClose();
      return;
    }

    setSelectedFiles(failedFiles);
    setFileErrors(nextFileErrors);

    if (successfulUploadCount > 0) {
      setUploadSummary(
        `${successfulUploadCount} dosya `
        + "başarıyla yüklendi. "
        + `${failedFiles.length} dosya `
        + "yüklenemedi.",
      );

      return;
    }

    setUploadSummary(
      `${failedFiles.length} dosya `
      + "yüklenemedi. Dosya ayrıntılarını "
      + "kontrol et.",
    );
  }


  return (
    <div
      className="modal-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (
          event.target
          === event.currentTarget
        ) {
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
            <p className="eyebrow">
              Yeni Kaynak
            </p>

            <h2 id="upload-modal-title">
              Doküman yükle
            </h2>
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
          className={
            `dropzone ${
              dragging
                ? "dropzone-active"
                : ""
            }`
          }
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

            addFiles(
              event.dataTransfer.files,
            );
          }}
        >
          <div className="dropzone-icon">
            {uploading ? (
              <LoaderCircle
                className="spinning-icon"
                size={34}
              />
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
            PDF, DOCX, TXT, CSV, XLSX,
            PNG ve JPG dosyaları
            yükleyebilirsin.
            Metin çıkarma, bölümleme ve
            anlamsal indeksleme işlemleri
            otomatik uygulanır.
          </p>

          <input
            ref={inputRef}
            type="file"
            multiple
            hidden
            disabled={uploading}
            accept={
              ".pdf,.docx,.txt,.csv,.xlsx,"
              + ".png,.jpg,.jpeg"
            }
            onChange={(event) => {
              addFiles(
                event.target.files,
              );
            }}
          />

          <button
            className={
              "secondary-btn "
              + "upload-select-button"
            }
            type="button"
            disabled={uploading}
            onClick={() => {
              inputRef.current?.click();
            }}
          >
            Dosya seç
          </button>
        </div>

        {selectedFiles.length > 0 && (
          <div
            ref={selectedFileListRef}
            className="selected-file-list"
          >
            <div className="selected-file-heading">
              <strong>
                {hasFileErrors
                  ? "Tekrar denenecek dosyalar"
                  : "Seçilen dosyalar"}
              </strong>

              <span>
                {selectedFiles.length} dosya
              </span>
            </div>

            {selectedFiles.map((file) => {
              const fileKey =
                getFileKey(file);

              const fileError =
                fileErrors[fileKey];

              const isActive =
                activeFileKey === fileKey;

              return (
                <div
                  className="selected-file-item"
                  key={fileKey}
                >
                  <span
                    className={
                      "selected-file-icon"
                    }
                  >
                    {isActive ? (
                      <LoaderCircle
                        className={
                          "spinning-icon"
                        }
                        size={17}
                      />
                    ) : (
                      <FileText size={17} />
                    )}
                  </span>

                  <span
                    className={
                      "selected-file-copy"
                    }
                  >
                    <strong>
                      {file.name}
                    </strong>

                    <span>
                      {isActive
                        ? "İşleniyor..."
                        : formatFileSize(
                            file.size,
                          )}
                    </span>

                    {fileError && (
                      <span
                        role="alert"
                        style={{
                          color: "#dc2626",
                          fontSize: "11px",
                          fontWeight: 500,
                          lineHeight: 1.45,
                          whiteSpace: "normal",
                        }}
                      >
                        {fileError}
                      </span>
                    )}
                  </span>

                  <button
                    type="button"
                    disabled={uploading}
                    aria-label={
                      `${file.name} `
                      + "dosyasını kaldır"
                    }
                    onClick={() => {
                      removeFile(file);
                    }}
                  >
                    <X size={15} />
                  </button>
                </div>
              );
            })}
          </div>
        )}

        {uploadSummary && (
          <div
            className="modal-api-error"
            role="alert"
          >
            {uploadSummary}
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
            disabled={
              selectedFiles.length === 0
              || uploading
            }
            onClick={() => {
              void submitUpload();
            }}
          >
            {uploading ? (
              <>
                <LoaderCircle
                  className="spinning-icon"
                  size={17}
                />
                İşleniyor
              </>
            ) : hasFileErrors ? (
              `${selectedFiles.length} `
              + "dosyayı tekrar dene"
            ) : selectedFiles.length > 0 ? (
              `${selectedFiles.length} `
              + "dosyayı yükle"
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
