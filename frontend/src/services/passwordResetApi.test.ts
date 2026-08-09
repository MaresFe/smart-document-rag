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
  confirmPasswordReset,
  getPasswordResetErrorMessage,
  previewPasswordReset,
  requestPasswordReset,
} from "./passwordResetApi";


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


describe("parola sıfırlama API istekleri", () => {
  it("sıfırlama bağlantısını e-posta ile ister", async () => {
    const response = {
      message: "Bağlantı gönderildiyse e-postanı kontrol et.",
    };

    axiosMocks.client.post.mockResolvedValueOnce({ data: response });

    await expect(
      requestPasswordReset("user@example.com"),
    ).resolves.toBe(response);
    expect(axiosMocks.client.post).toHaveBeenCalledWith(
      "/auth/password-reset/request",
      { email: "user@example.com" },
    );
  });

  it("token önizleme ve onay isteklerini gönderir", async () => {
    const preview = {
      expires_at: "2026-08-11T00:00:00Z",
    };

    axiosMocks.client.post
      .mockResolvedValueOnce({ data: preview })
      .mockResolvedValueOnce({ data: undefined });

    await expect(previewPasswordReset("reset-token")).resolves.toBe(preview);
    await expect(
      confirmPasswordReset("reset-token", "new-password"),
    ).resolves.toBeUndefined();

    expect(axiosMocks.client.post).toHaveBeenNthCalledWith(
      1,
      "/auth/password-reset/preview",
      { token: "reset-token" },
    );
    expect(axiosMocks.client.post).toHaveBeenNthCalledWith(
      2,
      "/auth/password-reset/confirm",
      {
        token: "reset-token",
        password: "new-password",
      },
    );
  });
});


describe("parola sıfırlama hata mesajları", () => {
  it.each([
    [new Error("local"), "Beklenmeyen bir hata oluştu."],
    [makeAxiosError(undefined, false), "Sunucuya ulaşılamadı. Backend servisinin çalıştığını kontrol et."],
    [makeAxiosError(400), "Parola yenileme bağlantısı geçersiz, süresi dolmuş veya daha önce kullanılmış."],
    [makeAxiosError(422), "Form alanlarını kontrol edip tekrar dene."],
    [makeAxiosError(500), "İşlem tamamlanamadı. Lütfen tekrar dene."],
  ])("beklenen mesajı döndürür", (error, expected) => {
    expect(getPasswordResetErrorMessage(error)).toBe(expected);
  });
});
