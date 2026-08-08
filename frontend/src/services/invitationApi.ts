import axios from "axios";


const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

const invitationClient = axios.create({
  baseURL: `${BACKEND_URL}/api`,
  timeout: 15_000,
  withCredentials: true,
  headers: {
    Accept: "application/json",
    "Content-Type": "application/json",
  },
});


export interface InvitationAcceptPayload {
  token: string;
  password: string;
  full_name: string;
}


export interface InvitationPreview {
  email: string;
  expires_at: string;
}


export async function getInvitationPreview(
  token: string,
): Promise<InvitationPreview> {
  const response = await invitationClient.post<InvitationPreview>(
    "/auth/invitations/preview",
    { token },
  );

  return response.data;
}


export async function acceptInvitation(
  payload: InvitationAcceptPayload,
): Promise<void> {
  await invitationClient.post(
    "/auth/invitations/accept",
    payload,
  );
}


export function getInvitationErrorMessage(
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
      "Davet bağlantısı geçersiz, süresi dolmuş "
      + "veya daha önce kullanılmış."
    );
  }

  if (error.response.status === 422) {
    return "Form alanlarını kontrol edip tekrar dene.";
  }

  return "Hesap oluşturulamadı. Lütfen tekrar dene.";
}
