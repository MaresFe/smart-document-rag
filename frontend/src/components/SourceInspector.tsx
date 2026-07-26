import {
  ChevronRight,
  FileText,
  Layers3,
  SearchCheck,
} from "lucide-react";

import type { ChatSourceRead } from "../types";

interface SourceInspectorProps {
  sources: ChatSourceRead[];
}

function clampSimilarity(
  value: number | null,
): number {
  return Math.max(
    0,
    Math.min(1, value ?? 0),
  );
}

function SourceInspector({
  sources,
}: SourceInspectorProps) {
  return (
    <div className="source-inspector-content">
      <div className="inspector-heading">
        <div>
          <p className="eyebrow">Yanıt Dayanakları</p>
          <h2>Kaynaklar</h2>
        </div>

        <span className="inspector-count">
          {sources.length}
        </span>
      </div>

      <p className="inspector-description">
        Yanıt oluşturulurken kullanılan en ilgili belge parçaları.
      </p>

      <div className="inspector-summary">
        <div className="inspector-summary-icon">
          <SearchCheck size={19} />
        </div>

        <div>
          <strong>
            {sources.length > 0
              ? "Kaynak doğrulaması hazır"
              : "Henüz kaynak bulunmuyor"}
          </strong>

          <span>
            {sources.length > 0
              ? `${sources.length} belge parçası eşleşti.`
              : "Bir soru gönderdiğinde eşleşen parçalar burada gösterilir."}
          </span>
        </div>
      </div>

      <div className="source-result-list">
        {sources.map((source, index) => {
          const similarity = clampSimilarity(
            source.similarity_score,
          );

          return (
            <article
              className="source-result-card"
              key={`${source.chunk_id}-${index}`}
            >
              <div className="source-result-topline">
                <span className="source-rank">
                  {index + 1}
                </span>

                <div className="source-file-icon">
                  <FileText size={17} />
                </div>

                <div className="source-file-copy">
                  <strong>
                    {source.original_filename}
                  </strong>

                  <span>
                    <Layers3 size={12} />
                    Parça {source.chunk_index}
                  </span>
                </div>
              </div>

              <div className="similarity-row">
                <div>
                  <span>Benzerlik</span>
                  <strong>
                    {Math.round(similarity * 100)}%
                  </strong>
                </div>

                <div
                  className="similarity-track"
                  aria-hidden="true"
                >
                  <span
                    style={{
                      width: `${similarity * 100}%`,
                    }}
                  />
                </div>
              </div>

              <p className="source-preview">
                {source.content}
              </p>

              <button
                className="source-detail-button"
                type="button"
              >
                Parçayı incele
                <ChevronRight size={15} />
              </button>
            </article>
          );
        })}
      </div>

      {sources.length > 0 && (
        <div className="inspector-footer-note">
          <Layers3 size={15} />
          Kaynak sıralaması semantik benzerlik skoruna göre yapılır.
        </div>
      )}
    </div>
  );
}

export default SourceInspector;