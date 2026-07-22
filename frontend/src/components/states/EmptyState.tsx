import { UploadCloud } from "lucide-react";

function EmptyState() {
  return (
    <div className="state-card">
      <UploadCloud size={42} />

      <h3>Henüz belge yüklenmedi</h3>

      <p>
        Başlamak için PDF veya DOCX dosyaları yükleyin.
      </p>
    </div>
  );
}

export default EmptyState;