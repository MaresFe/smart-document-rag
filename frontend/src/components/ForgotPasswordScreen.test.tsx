import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import ForgotPasswordScreen from "./ForgotPasswordScreen";


const passwordResetMocks = vi.hoisted(() => ({
  requestPasswordReset: vi.fn(),
  getPasswordResetErrorMessage: vi.fn(),
}));

vi.mock("../services/passwordResetApi", () => ({
  requestPasswordReset: passwordResetMocks.requestPasswordReset,
  getPasswordResetErrorMessage:
    passwordResetMocks.getPasswordResetErrorMessage,
}));


describe("ForgotPasswordScreen", () => {
  beforeEach(() => {
    passwordResetMocks.requestPasswordReset.mockReset();
    passwordResetMocks.getPasswordResetErrorMessage.mockReset();
  });

  it("boş e-posta adresini göndermeyi reddeder", async () => {
    const user = userEvent.setup();
    render(<ForgotPasswordScreen initialDark={false} />);

    await user.click(
      screen.getByRole("button", {
        name: "Yenileme bağlantısı gönder",
      }),
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "E-posta adresini gir.",
    );
    expect(
      passwordResetMocks.requestPasswordReset,
    ).not.toHaveBeenCalled();
  });

  it("normalleştirilmiş e-postayı gönderip genel başarı mesajı gösterir", async () => {
    const user = userEvent.setup();
    passwordResetMocks.requestPasswordReset.mockResolvedValue({
      message: "ok",
    });
    render(<ForgotPasswordScreen initialDark={false} />);

    await user.type(
      screen.getByRole("textbox", { name: "E-posta" }),
      "  USER@EXAMPLE.COM  ",
    );
    await user.click(
      screen.getByRole("button", {
        name: "Yenileme bağlantısı gönder",
      }),
    );

    expect(
      passwordResetMocks.requestPasswordReset,
    ).toHaveBeenCalledWith("user@example.com");
    expect(await screen.findByRole("status")).toHaveTextContent(
      "İsteğiniz alındı.",
    );
    expect(screen.getByRole("status")).toHaveTextContent(
      "bir hesap varsa",
    );
  });

  it("servis hatasını kullanıcıya çevirir", async () => {
    const user = userEvent.setup();
    const requestError = new Error("network");
    passwordResetMocks.requestPasswordReset.mockRejectedValue(
      requestError,
    );
    passwordResetMocks.getPasswordResetErrorMessage.mockReturnValue(
      "Sunucuya ulaşılamadı.",
    );
    render(<ForgotPasswordScreen initialDark />);

    await user.type(
      screen.getByRole("textbox", { name: "E-posta" }),
      "user@example.com",
    );
    await user.click(
      screen.getByRole("button", {
        name: "Yenileme bağlantısı gönder",
      }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Sunucuya ulaşılamadı.",
    );
    expect(
      passwordResetMocks.getPasswordResetErrorMessage,
    ).toHaveBeenCalledWith(requestError);
  });
});
