import axios from "axios";


const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

const adminClient = axios.create({
  baseURL: `${BACKEND_URL}/api`,
  timeout: 15_000,
  withCredentials: true,
  headers: {
    Accept: "application/json",
    "Content-Type": "application/json",
  },
});


export interface AdminUserRead {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_admin: boolean;
  email_verified_at: string | null;
  created_at: string;
  updated_at: string;
}


export interface InvitationRead {
  id: string;
  email: string;
  expires_at: string;
  created_at: string;
  delivery_mode: string;
  invitation_url: string | null;
}


export async function getAdminUsers(): Promise<AdminUserRead[]> {
  const response = await adminClient.get<AdminUserRead[]>(
    "/admin/users",
  );

  return response.data;
}


export async function updateAdminUserStatus(
  userId: string,
  isActive: boolean,
): Promise<AdminUserRead> {
  const response = await adminClient.patch<AdminUserRead>(
    `/admin/users/${userId}`,
    { is_active: isActive },
  );

  return response.data;
}


export async function createUserInvitation(
  email: string,
): Promise<InvitationRead> {
  const response = await adminClient.post<InvitationRead>(
    "/auth/invitations",
    { email },
  );

  return response.data;
}


export function getAdminErrorMessage(
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

  if (error.response.status === 401) {
    return "Oturumunuz sona ermiş. Yeniden giriş yapın.";
  }

  if (error.response.status === 403) {
    return "Bu işlem için yönetici yetkisi gerekiyor.";
  }

  if (error.response.status === 409) {
    return "Bu e-posta adresiyle zaten bir hesap bulunuyor.";
  }

  if (error.response.status === 502) {
    return "Davet e-postası gönderilemedi.";
  }

  const responseData = error.response.data as
    | { detail?: unknown }
    | undefined;
  const detail = responseData?.detail;

  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  return "İşlem tamamlanamadı. Lütfen tekrar deneyin.";
}
