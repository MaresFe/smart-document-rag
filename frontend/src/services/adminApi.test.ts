import { beforeEach, describe, expect, it, vi } from "vitest";


const axiosMocks = vi.hoisted(() => {
  const client = {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  };
  const create = vi.fn(() => client);
  const isAxiosError = vi.fn(
    (error: unknown) => (
      typeof error === "object"
      && error !== null
      && "isAxiosError" in error
      && error.isAxiosError === true
    ),
  );

  return { client, create, isAxiosError };
});


vi.mock("axios", () => ({
  default: {
    create: axiosMocks.create,
    isAxiosError: axiosMocks.isAxiosError,
  },
}));


import {
  createUserInvitation,
  getAdminErrorMessage,
  getAdminUsers,
  updateAdminUserStatus,
} from "./adminApi";


function makeAxiosError(
  status?: number,
  detail?: unknown,
  includeResponse = true,
): object {
  return {
    isAxiosError: true,
    response: includeResponse
      ? { status: status ?? 500, data: { detail } }
      : undefined,
  };
}


beforeEach(() => {
  axiosMocks.client.get.mockReset();
  axiosMocks.client.post.mockReset();
  axiosMocks.client.patch.mockReset();
  axiosMocks.isAxiosError.mockClear();
});


describe("yönetici API istekleri", () => {
  it("kullanıcıları listeler ve hesap durumunu değiştirir", async () => {
    const users = [{ id: "user-1" }] as Awaited<
      ReturnType<typeof getAdminUsers>
    >;
    const updatedUser = {
      id: "user-1",
      is_active: false,
    } as Awaited<ReturnType<typeof updateAdminUserStatus>>;

    axiosMocks.client.get.mockResolvedValueOnce({ data: users });
    axiosMocks.client.patch.mockResolvedValueOnce({ data: updatedUser });

    await expect(getAdminUsers()).resolves.toBe(users);
    await expect(
      updateAdminUserStatus("user-1", false),
    ).resolves.toBe(updatedUser);

    expect(axiosMocks.client.get).toHaveBeenCalledWith("/admin/users");
    expect(axiosMocks.client.patch).toHaveBeenCalledWith(
      "/admin/users/user-1",
      { is_active: false },
    );
  });

  it("davet isteğini normalize edilmiş payload ile gönderir", async () => {
    const invitation = { id: "invite-1" } as Awaited<
      ReturnType<typeof createUserInvitation>
    >;

    axiosMocks.client.post.mockResolvedValueOnce({ data: invitation });

    await expect(
      createUserInvitation("user@example.com"),
    ).resolves.toBe(invitation);
    expect(axiosMocks.client.post).toHaveBeenCalledWith(
      "/auth/invitations",
      { email: "user@example.com" },
    );
  });
});


describe("yönetici API hata mesajları", () => {
  it.each([
    [new Error("local"), "Beklenmeyen bir hata oluştu."],
    [makeAxiosError(undefined, undefined, false), "Sunucuya ulaşılamadı. Backend servisinin çalıştığını kontrol et."],
    [makeAxiosError(401), "Oturumunuz sona ermiş. Yeniden giriş yapın."],
    [makeAxiosError(403), "Bu işlem için yönetici yetkisi gerekiyor."],
    [makeAxiosError(409), "Bu e-posta adresiyle zaten bir hesap bulunuyor."],
    [makeAxiosError(502), "Davet e-postası gönderilemedi."],
    [makeAxiosError(500, "Özel hata"), "Özel hata"],
    [makeAxiosError(500, { message: "ignored" }), "İşlem tamamlanamadı. Lütfen tekrar deneyin."],
  ])("beklenen mesajı döndürür", (error, expected) => {
    expect(getAdminErrorMessage(error)).toBe(expected);
  });
});
