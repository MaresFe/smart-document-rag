import axios from "axios";


const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

const passwordResetClient = axios.create({
  baseURL: `${BACKEND_URL}/api`,
  timeout: 15_000,
  withCredentials: true,
  headers: {
    Accept: "application/json",
    "Content-Type": "application/json",
  },
});


export interface PasswordResetPreview {
  expires_at: string;
}


interface PasswordResetRequestResponse {
  message: string;
}


export async function requestPasswordReset(
  email: string,
): Promise<PasswordResetRequestResponse> {
  const response =
    await passwordResetClient.post<PasswordResetRequestResponse>(
      "/auth/password-reset/request",
      { email },
    );

  return response.data;
}


export async function previewPasswordReset(
  token: string,
): Promise<PasswordResetPreview> {
  const response =
    await passwordResetClient.post<PasswordResetPreview>(
      "/auth/password-reset/preview",
      { token },
    );

  return response.data;
}


export async function confirmPasswordReset(
  token: string,
  password: string,
): Promise<void> {
  await passwordResetClient.post(
    "/auth/password-reset/confirm",
    { token, password },
  );
}


export function getPasswordResetErrorMessage(
  error: unknown,
): string {
  if (!axios.isAxiosError(error)) {
    return "Beklenmeyen bir hata oluştu.";
  }

  if (!error.response) {
    return (
      "Sunucuya ulaşılamadı. Backend servisinin "
      + "çalıştığını kontrol et."
    );
  }

  if (error.response.status === 400) {
    return (
      "Parola yenileme bağlantısı geçersiz, süresi "
      + "dolmuş veya daha önce kullanılmış."
    );
  }

  if (error.response.status === 422) {
    return "Form alanlarını kontrol edip tekrar dene.";
  }

  return "İşlem tamamlanamadı. Lütfen tekrar dene.";
}

