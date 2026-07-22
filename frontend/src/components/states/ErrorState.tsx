import { TriangleAlert } from "lucide-react";

function ErrorState() {
  return (
    <div className="state-card state-error">
      <TriangleAlert size={42} />

      <h3>Bir hata oluştu</h3>

      <p>
        Kaynaklar alınamadı. Lütfen tekrar deneyin.
      </p>
    </div>
  );
}

export default ErrorState;