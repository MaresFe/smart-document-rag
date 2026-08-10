import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import PasswordResetScreen from "./PasswordResetScreen";


const passwordResetMocks = vi.hoisted(() => ({
  previewPasswordReset: vi.fn(),
  confirmPasswordReset: vi.fn(),
  getPasswordResetErrorMessage: vi.fn(),
}));

vi.mock("../services/passwordResetApi", () => ({
  previewPasswordReset: passwordResetMocks.previewPasswordReset,
  confirmPasswordReset: passwordResetMocks.confirmPasswordReset,
  getPasswordResetErrorMessage:
    passwordResetMocks.getPasswordResetErrorMessage,
}));


describe("PasswordResetScreen", () => {
  beforeEach(() => {
    passwordResetMocks.previewPasswordReset.mockReset();
    passwordResetMocks.confirmPasswordReset.mockReset();
    passwordResetMocks.getPasswordResetErrorMessage.mockReset();
  });

  it("token olmayan bağlantı için yeni bağlantı önerir", () => {
    render(<PasswordResetScreen token={null} initialDark={false} />);

    expect(screen.getByRole("alert")).toHaveTextContent(
      "geçerli bir token bulunamadı",
    );
    expect(
      screen.getByRole("link", { name: "Yeni bağlantı iste" }),
    ).toHaveAttribute("href", "/forgot-password");
  });

  it("geçersiz token hatasını gösterir", async () => {
    const requestError = new Error("expired");
    passwordResetMocks.previewPasswordReset.mockRejectedValue(
      requestError,
    );
    passwordResetMocks.getPasswordResetErrorMessage.mockReturnValue(
      "Bağlantının süresi doldu.",
    );
    render(
      <PasswordResetScreen token="expired-token" initialDark={false} />,
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Bağlantının süresi doldu.",
    );
  });

  it("parola kurallarını doğrulayıp yeni parolayı kaydeder", async () => {
    const user = userEvent.setup();
    passwordResetMocks.previewPasswordReset.mockResolvedValue({
      expires_at: "2026-08-11T10:00:00Z",
    });
    passwordResetMocks.confirmPasswordReset.mockResolvedValue(undefined);
    const nativeSetTimeout = window.setTimeout;
    const timeoutSpy = vi
      .spyOn(window, "setTimeout")
      .mockImplementation((handler, timeout, ...arguments_) => {
        if (timeout === 1200) {
          return 1 as unknown as ReturnType<
            typeof window.setTimeout
          >;
        }

        return nativeSetTimeout(handler, timeout, ...arguments_);
      });
    render(
      <PasswordResetScreen token="reset-token" initialDark={false} />,
    );

    const passwordInput = await screen.findByLabelText("Yeni parola");
    const confirmationInput = screen.getByLabelText(
      "Yeni parolayı doğrula",
    );

    await user.type(passwordInput, "short");
    await user.click(
      screen.getByRole("button", { name: "Parolayı değiştir" }),
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Parola en az 10 karakter olmalıdır.",
    );

    await user.clear(passwordInput);
    await user.type(passwordInput, "strong-pass-2");
    await user.type(confirmationInput, "different-pass");
    await user.click(
      screen.getByRole("button", { name: "Parolayı değiştir" }),
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Parolalar birbiriyle eşleşmiyor.",
    );

    await user.clear(confirmationInput);
    await user.type(confirmationInput, "strong-pass-2");
    await user.click(
      screen.getByRole("button", { name: "Parolayı değiştir" }),
    );

    expect(passwordResetMocks.confirmPasswordReset).toHaveBeenCalledWith(
      "reset-token",
      "strong-pass-2",
    );
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Parolanız değiştirildi.",
    );
    expect(timeoutSpy).toHaveBeenCalledWith(expect.any(Function), 1200);

    timeoutSpy.mockRestore();
  });
});
