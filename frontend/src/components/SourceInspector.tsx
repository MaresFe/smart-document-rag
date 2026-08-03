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

const MINIMUM_VISIBLE_SIMILARITY = 0.75;

function clampSimilarity(
  value: number | null,
): number {
  return Math.max(
    0,
    Math.min(1, value ?? 0),
  );
}

function getMatchLabel(
  similarity: number,
): string {
  if (similarity >= 0.9) {
    return "Çok güçlü";
  }

  if (similarity >= 0.82) {
    return "Güçlü";
  }

  return "Yeterli";
}

function SourceInspector({
  sources,
}: SourceInspectorProps) {
  const visibleSources = sources.filter(
    (source) =>
      clampSimilarity(
        source.similarity_score,
      ) >= MINIMUM_VISIBLE_SIMILARITY,
  );

  return (
    <div className="source-inspector-content">
      <div className="inspector-heading">
        <div>
          <p className="eyebrow">
            Yanıt Dayanakları
          </p>

          <h2>Kaynaklar</h2>
        </div>

        <span className="inspector-count">
          {visibleSources.length}
        </span>
      </div>

      <p className="inspector-description">
        Yanıt oluşturulurken kullanılan ilgili
        belge parçaları.
      </p>

      <div className="inspector-summary">
        <div className="inspector-summary-icon">
          <SearchCheck size={19} />
        </div>

        <div>
          <strong>
            {visibleSources.length > 0
              ? "Kaynak doğrulaması hazır"
              : "Uygun kaynak bulunmuyor"}
          </strong>

          <span>
            {visibleSources.length > 0
              ? `${visibleSources.length} belge parçası eşleşti.`
              : "Seçilen yanıt için yeterince ilgili bir belge parçası bulunamadı."}
          </span>
        </div>
      </div>

      <div className="source-result-list">
        {visibleSources.map(
          (source, index) => {
            const similarity =
              clampSimilarity(
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
                      {source.original_filename ??
                        "Dosya adı bilinmiyor"}
                    </strong>

                    <span>
                      <Layers3 size={12} />
                      Parça {source.chunk_index}
                    </span>
                  </div>
                </div>

                <div className="similarity-row">
                  <div>
                    <span>
                      Anlamsal eşleşme
                    </span>

                    <strong>
                      {getMatchLabel(
                        similarity,
                      )}
                    </strong>
                  </div>

                  <div
                    className="similarity-track"
                    aria-label={
                      `Anlamsal eşleşme: ` +
                      getMatchLabel(
                        similarity,
                      )
                    }
                  >
                    <span
                      style={{
                        width:
                          `${similarity * 100}%`,
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
          },
        )}
      </div>

      {visibleSources.length > 0 && (
        <div className="inspector-footer-note">
          <Layers3 size={15} />

          <span>
            Kaynaklar anlamsal yakınlığa göre
            sıralanır. Bu sıralama yanıtın
            doğruluğunu garanti etmez.
          </span>
        </div>
      )}
    </div>
  );
}

export default SourceInspector;