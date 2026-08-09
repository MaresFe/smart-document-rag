import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import WorkspaceDialog from "./WorkspaceDialog";


describe("WorkspaceDialog", () => {
  it("dialog yokken görünmez", () => {
    const { container } = render(
      <WorkspaceDialog
        dialog={null}
        busy={false}
        error={null}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
      />,
    );

    expect(container).toBeEmptyDOMElement();
  });

  it("sohbet adını kırpar ve başarılı işlemden sonra kapanır", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    const onConfirm = vi.fn().mockResolvedValue(true);
    render(
      <WorkspaceDialog
        dialog={{
          type: "rename-session",
          targetId: "session-id",
          targetName: "Eski ad",
        }}
        busy={false}
        error={null}
        onClose={onClose}
        onConfirm={onConfirm}
      />,
    );

    const input = screen.getByRole("textbox", { name: "Sohbet adı" });
    await user.clear(input);
    await user.type(input, "  Yeni sohbet adı  ");
    await user.click(screen.getByRole("button", { name: "Kaydet" }));

    expect(onConfirm).toHaveBeenCalledWith("Yeni sohbet adı");
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("başarısız işlemde açık kalır ve API hatasını gösterir", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    const onConfirm = vi.fn().mockResolvedValue(false);
    render(
      <WorkspaceDialog
        dialog={{
          type: "delete-document",
          targetId: "document-id",
          targetName: "rapor.pdf",
        }}
        busy={false}
        error="Belge silinemedi."
        onClose={onClose}
        onConfirm={onConfirm}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Belge silinemedi.",
    );
    expect(screen.getByText("Bu işlem geri alınamaz.")).toBeVisible();

    await user.click(screen.getByRole("button", { name: "Sil" }));

    expect(onConfirm).toHaveBeenCalledWith("rapor.pdf");
    expect(onClose).not.toHaveBeenCalled();
  });

  it("boştaki arka plan ve Escape ile kapanır, yoğunken kapanmaz", () => {
    const onClose = vi.fn();
    const { container, rerender } = render(
      <WorkspaceDialog
        dialog={{
          type: "delete-session",
          targetId: "session-id",
          targetName: "Sohbet",
        }}
        busy={false}
        error={null}
        onClose={onClose}
        onConfirm={vi.fn()}
      />,
    );
    const backdrop = container.querySelector(".modal-backdrop");

    if (!backdrop) {
      throw new Error("Modal arka planı bulunamadı.");
    }

    fireEvent.mouseDown(backdrop);
    fireEvent.keyDown(backdrop, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(2);

    rerender(
      <WorkspaceDialog
        dialog={{
          type: "delete-session",
          targetId: "session-id",
          targetName: "Sohbet",
        }}
        busy
        error={null}
        onClose={onClose}
        onConfirm={vi.fn()}
      />,
    );
    fireEvent.mouseDown(backdrop);
    fireEvent.keyDown(backdrop, { key: "Escape" });

    expect(onClose).toHaveBeenCalledTimes(2);
    expect(screen.getByRole("button", { name: "İşleniyor" })).toBeDisabled();
  });
});
