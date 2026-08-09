import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import AuthScreen from "./AuthScreen";


function renderAuthScreen(
  overrides: Partial<React.ComponentProps<typeof AuthScreen>> = {},
) {
  const props: React.ComponentProps<typeof AuthScreen> = {
    dark: false,
    submitting: false,
    error: null,
    onLogin: vi.fn().mockResolvedValue(undefined),
    onRegister: vi.fn().mockResolvedValue(undefined),
    onClearError: vi.fn(),
    onThemeToggle: vi.fn(),
    ...overrides,
  };

  render(<AuthScreen {...props} />);

  return props;
}


describe("AuthScreen", () => {
  it("zorunlu giriş alanlarını sırayla doğrular", async () => {
    const user = userEvent.setup();
    const props = renderAuthScreen();
    const submitButton = screen.getByRole("button", {
      name: "Giriş yap",
    });

    await user.click(submitButton);

    expect(screen.getByRole("alert")).toHaveTextContent(
      "E-posta adresini gir.",
    );

    await user.type(
      screen.getByRole("textbox", { name: "E-posta" }),
      "user@example.com",
    );
    await user.click(submitButton);

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Parolanı gir.",
    );
    expect(props.onLogin).not.toHaveBeenCalled();
  });

  it("e-postayı normalleştirip giriş isteğini gönderir", async () => {
    const user = userEvent.setup();
    const props = renderAuthScreen();

    await user.type(
      screen.getByRole("textbox", { name: "E-posta" }),
      "  USER@EXAMPLE.COM  ",
    );
    await user.type(screen.getByLabelText("Parola"), "strong-password");
    await user.click(
      screen.getByRole("button", { name: "Giriş yap" }),
    );

    expect(props.onClearError).toHaveBeenCalledOnce();
    expect(props.onLogin).toHaveBeenCalledWith({
      email: "user@example.com",
      password: "strong-password",
    });
  });

  it("işlem sırasında formu kilitler ve API hatasını gösterir", () => {
    renderAuthScreen({
      submitting: true,
      error: "Giriş yapılamadı.",
    });

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Giriş yapılamadı.",
    );
    expect(
      screen.getByRole("button", { name: "Giriş yapılıyor..." }),
    ).toBeDisabled();
    expect(
      screen.getByRole("link", { name: "Parolamı unuttum" }),
    ).toHaveAttribute("href", "/forgot-password");
  });
});
