import {
  ChevronRight,
  ExternalLink,
  FileText,
  Layers3,
  SearchCheck,
} from "lucide-react";

const sources = [
  {
    id: 1,
    filename: "company.pdf",
    similarity: 0.91,
    chunk: 4,
    content:
      "Şirket, mobil iletişim çözümleri ve kurumsal yazılım hizmetleri alanında faaliyet göstermektedir. Proje süreçlerinde ölçeklenebilirlik, güvenilirlik ve kullanıcı deneyimi önceliklidir.",
  },
  {
    id: 2,
    filename: "rag-notes.docx",
    similarity: 0.87,
    chunk: 8,
    content:
      "Embedding vektörleri PostgreSQL üzerinde pgvector uzantısı kullanılarak document_chunks tablosunda saklanır ve benzerlik araması cosine distance üzerinden gerçekleştirilir.",
  },
];

function SourceInspector() {
  return (
    <div className="source-inspector-content">
      <div className="inspector-heading">
        <div>
          <p className="eyebrow">Yanıt Dayanakları</p>
          <h2>Kaynaklar</h2>
        </div>

        <span className="inspector-count">2</span>
      </div>

      <p className="inspector-description">
        Yanıt oluşturulurken kullanılan en ilgili belge parçaları.
      </p>

      <div className="inspector-summary">
        <div className="inspector-summary-icon">
          <SearchCheck size={19} />
        </div>

        <div>
          <strong>Kaynak doğrulaması hazır</strong>
          <span>2 belge parçası eşleşti.</span>
        </div>
      </div>

      <div className="source-result-list">
        {sources.map((source, index) => (
          <article className="source-result-card" key={source.id}>
            <div className="source-result-topline">
              <span className="source-rank">{index + 1}</span>

              <div className="source-file-icon">
                <FileText size={17} />
              </div>

              <div className="source-file-copy">
                <strong>{source.filename}</strong>

                <span>
                  <Layers3 size={12} />
                  Parça {source.chunk}
                </span>
              </div>

              <button
                className="source-open-button"
                type="button"
                aria-label={`${source.filename} kaynağını aç`}
                title="Kaynağı aç"
              >
                <ExternalLink size={15} />
              </button>
            </div>

            <div className="similarity-row">
              <div>
                <span>Benzerlik</span>
                <strong>{Math.round(source.similarity * 100)}%</strong>
              </div>

              <div className="similarity-track" aria-hidden="true">
                <span
                  style={{
                    width: `${source.similarity * 100}%`,
                  }}
                />
              </div>
            </div>

            <p className="source-preview">{source.content}</p>

            <button className="source-detail-button" type="button">
              Parçayı incele
              <ChevronRight size={15} />
            </button>
          </article>
        ))}
      </div>

      <div className="inspector-footer-note">
        <Layers3 size={15} />
        Kaynak sıralaması semantik benzerlik skoruna göre yapılır.
      </div>
    </div>
  );
}

export default SourceInspector;