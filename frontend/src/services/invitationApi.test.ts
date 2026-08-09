import { beforeEach, describe, expect, it, vi } from "vitest";


const axiosMocks = vi.hoisted(() => {
  const client = { post: vi.fn() };
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
  acceptInvitation,
  getInvitationErrorMessage,
  getInvitationPreview,
} from "./invitationApi";


function makeAxiosError(
  status?: number,
  includeResponse = true,
): object {
  return {
    isAxiosError: true,
    response: includeResponse
      ? { status: status ?? 500 }
      : undefined,
  };
}


beforeEach(() => {
  axiosMocks.client.post.mockReset();
  axiosMocks.isAxiosError.mockClear();
});


describe("davet API istekleri", () => {
  it("davet önizlemesini token ile ister", async () => {
    const preview = {
      email: "user@example.com",
      expires_at: "2026-08-11T00:00:00Z",
    };

    axiosMocks.client.post.mockResolvedValueOnce({ data: preview });

    await expect(getInvitationPreview("invite-token")).resolves.toBe(preview);
    expect(axiosMocks.client.post).toHaveBeenCalledWith(
      "/auth/invitations/preview",
      { token: "invite-token" },
    );
  });

  it("daveti hesap bilgileriyle kabul eder", async () => {
    const payload = {
      token: "invite-token",
      password: "secure-password",
      full_name: "Test Kullanıcısı",
    };

    axiosMocks.client.post.mockResolvedValueOnce({ data: undefined });

    await expect(acceptInvitation(payload)).resolves.toBeUndefined();
    expect(axiosMocks.client.post).toHaveBeenCalledWith(
      "/auth/invitations/accept",
      payload,
    );
  });
});


describe("davet hata mesajları", () => {
  it.each([
    [new Error("local"), "Beklenmeyen bir hata oluştu."],
    [makeAxiosError(undefined, false), "Sunucuya ulaşılamadı. Backend servisinin çalıştığını kontrol et."],
    [makeAxiosError(400), "Davet bağlantısı geçersiz, süresi dolmuş veya daha önce kullanılmış."],
    [makeAxiosError(422), "Form alanlarını kontrol edip tekrar dene."],
    [makeAxiosError(500), "Hesap oluşturulamadı. Lütfen tekrar dene."],
  ])("beklenen mesajı döndürür", (error, expected) => {
    expect(getInvitationErrorMessage(error)).toBe(expected);
  });
});
