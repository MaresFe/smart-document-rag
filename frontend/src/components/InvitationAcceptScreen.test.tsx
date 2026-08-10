import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import InvitationAcceptScreen from "./InvitationAcceptScreen";


const invitationMocks = vi.hoisted(() => ({
  getInvitationPreview: vi.fn(),
  acceptInvitation: vi.fn(),
  getInvitationErrorMessage: vi.fn(),
}));

vi.mock("../services/invitationApi", () => ({
  getInvitationPreview: invitationMocks.getInvitationPreview,
  acceptInvitation: invitationMocks.acceptInvitation,
  getInvitationErrorMessage:
    invitationMocks.getInvitationErrorMessage,
}));


describe("InvitationAcceptScreen", () => {
  beforeEach(() => {
    invitationMocks.getInvitationPreview.mockReset();
    invitationMocks.acceptInvitation.mockReset();
    invitationMocks.getInvitationErrorMessage.mockReset();
  });

  it("token olmayan bağlantıyı reddeder", () => {
    render(
      <InvitationAcceptScreen token={null} initialDark={false} />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Geçerli bir davet tokenı bulunamadı.",
    );
    expect(
      invitationMocks.getInvitationPreview,
    ).not.toHaveBeenCalled();
  });

  it("davet önizlemesini yükleyip form kurallarını uygular", async () => {
    const user = userEvent.setup();
    invitationMocks.getInvitationPreview.mockResolvedValue({
      email: "invited@example.com",
      expires_at: "2026-08-11T10:00:00Z",
    });
    render(
      <InvitationAcceptScreen token="invite-token" initialDark={false} />,
    );

    expect(
      await screen.findByDisplayValue("invited@example.com"),
    ).toHaveAttribute("readonly");

    await user.click(
      screen.getByRole("button", { name: "Daveti kabul et" }),
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Ad ve soyad alanını doldur.",
    );

    await user.type(screen.getByLabelText("Ad ve soyad"), "Ada Lovelace");
    await user.click(
      screen.getByRole("button", { name: "Daveti kabul et" }),
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Parola en az 10 karakter olmalıdır.",
    );
  });

  it("hesabı normalleştirilmiş adla oluşturur", async () => {
    const user = userEvent.setup();
    invitationMocks.getInvitationPreview.mockResolvedValue({
      email: "invited@example.com",
      expires_at: "2026-08-11T10:00:00Z",
    });
    invitationMocks.acceptInvitation.mockResolvedValue(undefined);
    const nativeSetTimeout = window.setTimeout;
    const timeoutSpy = vi
      .spyOn(window, "setTimeout")
      .mockImplementation((handler, timeout, ...arguments_) => {
        if (timeout === 700) {
          return 1 as unknown as ReturnType<
            typeof window.setTimeout
          >;
        }

        return nativeSetTimeout(handler, timeout, ...arguments_);
      });
    render(
      <InvitationAcceptScreen token="invite-token" initialDark />,
    );

    await screen.findByDisplayValue("invited@example.com");
    await user.type(
      screen.getByLabelText("Ad ve soyad"),
      "  Ada   Lovelace  ",
    );
    await user.type(screen.getByLabelText("Parola"), "strong-pass-1");
    await user.type(
      screen.getByLabelText("Parolayı doğrula"),
      "strong-pass-1",
    );
    await user.click(
      screen.getByRole("button", { name: "Daveti kabul et" }),
    );

    expect(invitationMocks.acceptInvitation).toHaveBeenCalledWith({
      token: "invite-token",
      password: "strong-pass-1",
      full_name: "Ada Lovelace",
    });
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Hesabınız oluşturuldu.",
    );
    expect(timeoutSpy).toHaveBeenCalledWith(expect.any(Function), 700);

    timeoutSpy.mockRestore();
  });
});
