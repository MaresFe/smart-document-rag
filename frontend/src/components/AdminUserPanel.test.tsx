import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import type { UserRead } from "../types";
import AdminUserPanel from "./AdminUserPanel";


const adminMocks = vi.hoisted(() => ({
  getAdminUsers: vi.fn(),
  updateAdminUserStatus: vi.fn(),
  createUserInvitation: vi.fn(),
  getAdminErrorMessage: vi.fn(),
}));

vi.mock("../services/adminApi", () => ({
  getAdminUsers: adminMocks.getAdminUsers,
  updateAdminUserStatus: adminMocks.updateAdminUserStatus,
  createUserInvitation: adminMocks.createUserInvitation,
  getAdminErrorMessage: adminMocks.getAdminErrorMessage,
}));

const currentUser: UserRead = {
  id: "admin-id",
  email: "admin@example.com",
  full_name: "Admin User",
  is_active: true,
  is_admin: true,
  email_verified_at: "2026-08-01T10:00:00Z",
  created_at: "2026-08-01T10:00:00Z",
};

const regularUser = {
  id: "user-id",
  email: "user@example.com",
  full_name: "Regular User",
  is_active: true,
  is_admin: false,
  email_verified_at: "2026-08-02T10:00:00Z",
  created_at: "2026-08-02T10:00:00Z",
  updated_at: "2026-08-02T10:00:00Z",
};

const adminUser = {
  ...currentUser,
  updated_at: "2026-08-01T10:00:00Z",
};


describe("AdminUserPanel", () => {
  beforeEach(() => {
    adminMocks.getAdminUsers.mockReset();
    adminMocks.updateAdminUserStatus.mockReset();
    adminMocks.createUserInvitation.mockReset();
    adminMocks.getAdminErrorMessage.mockReset();
    adminMocks.getAdminUsers.mockResolvedValue([
      regularUser,
      adminUser,
    ]);
  });

  it("kapalıyken içerik oluşturmaz", () => {
    const { container } = render(
      <AdminUserPanel
        currentUser={currentUser}
        open={false}
        onClose={vi.fn()}
      />,
    );

    expect(container).toBeEmptyDOMElement();
    expect(adminMocks.getAdminUsers).not.toHaveBeenCalled();
  });

  it("kullanıcıları yükler, arar ve mevcut hesabı korur", async () => {
    const user = userEvent.setup();
    render(
      <AdminUserPanel
        currentUser={currentUser}
        open
        onClose={vi.fn()}
      />,
    );

    expect(await screen.findByText("Regular User")).toBeVisible();
    expect(screen.getByText("Mevcut hesap")).toBeVisible();

    await user.type(
      screen.getByPlaceholderText("Kullanıcı ara"),
      "admin@example.com",
    );

    expect(screen.queryByText("Regular User")).not.toBeInTheDocument();
    expect(screen.getByText("Admin User")).toBeVisible();
  });

  it("davet e-postasını normalleştirir ve bağlantıyı kopyalar", async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });
    adminMocks.createUserInvitation.mockResolvedValue({
      id: "invitation-id",
      email: "new@example.com",
      expires_at: "2026-08-11T10:00:00Z",
      created_at: "2026-08-10T10:00:00Z",
      delivery_mode: "console",
      invitation_url: "http://localhost:5173/accept-invitation?token=abc",
    });
    render(
      <AdminUserPanel
        currentUser={currentUser}
        open
        onClose={vi.fn()}
      />,
    );

    await screen.findByText("Regular User");
    await user.type(
      screen.getByPlaceholderText("kullanici@sirket.com"),
      "  NEW@EXAMPLE.COM  ",
    );
    await user.click(
      screen.getByRole("button", { name: "Davet gönder" }),
    );

    expect(adminMocks.createUserInvitation).toHaveBeenCalledWith(
      "new@example.com",
    );
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Davet oluşturuldu",
    );

    await user.click(
      screen.getByRole("button", { name: "Bağlantıyı kopyala" }),
    );

    expect(writeText).toHaveBeenCalledWith(
      "http://localhost:5173/accept-invitation?token=abc",
    );
    expect(screen.getByRole("button", { name: "Kopyalandı" })).toBeVisible();
  });

  it("kullanıcı durumunu iki adımlı onayla değiştirir", async () => {
    const user = userEvent.setup();
    adminMocks.updateAdminUserStatus.mockResolvedValue({
      ...regularUser,
      is_active: false,
    });
    render(
      <AdminUserPanel
        currentUser={currentUser}
        open
        onClose={vi.fn()}
      />,
    );

    await screen.findByText("Regular User");
    await user.click(
      screen.getByRole("button", { name: "Pasifleştir" }),
    );

    expect(adminMocks.updateAdminUserStatus).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Onayla" }));

    await waitFor(() => {
      expect(adminMocks.updateAdminUserStatus).toHaveBeenCalledWith(
        "user-id",
        false,
      );
    });
    expect(screen.getByText("Pasif")).toBeVisible();
  });
});
