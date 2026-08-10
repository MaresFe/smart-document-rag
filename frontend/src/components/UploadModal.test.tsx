import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import UploadModal from "./UploadModal";


function getFileInput(container: HTMLElement): HTMLInputElement {
  const input = container.querySelector<HTMLInputElement>(
    'input[type="file"]',
  );

  if (!input) {
    throw new Error("Dosya alanı bulunamadı.");
  }

  return input;
}


describe("UploadModal", () => {
  it("kapalıyken görünmez", () => {
    const { container } = render(
      <UploadModal open={false} onClose={vi.fn()} onUpload={vi.fn()} />,
    );

    expect(container).toBeEmptyDOMElement();
  });

  it("aynı dosyanın ikinci kez seçilmesini engeller", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <UploadModal open onClose={vi.fn()} onUpload={vi.fn()} />,
    );
    const input = getFileInput(container);
    const file = new File(["rapor"], "rapor.txt", {
      type: "text/plain",
      lastModified: 100,
    });

    await user.upload(input, file);
    await user.upload(input, file);

    expect(screen.getByText("1 dosya")).toBeVisible();
    expect(screen.getAllByText("rapor.txt")).toHaveLength(1);
  });

  it("dosyaları sırayla yükler ve tümü başarılıysa kapanır", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    const onUpload = vi.fn().mockResolvedValue(undefined);
    const { container } = render(
      <UploadModal open onClose={onClose} onUpload={onUpload} />,
    );
    const firstFile = new File(["a"], "a.txt", {
      type: "text/plain",
    });
    const secondFile = new File(["b"], "b.pdf", {
      type: "application/pdf",
    });

    await user.upload(getFileInput(container), [firstFile, secondFile]);
    await user.click(
      screen.getByRole("button", { name: "2 dosyayı yükle" }),
    );

    await waitFor(() => {
      expect(onUpload).toHaveBeenCalledTimes(2);
    });
    expect(onUpload).toHaveBeenNthCalledWith(1, [firstFile]);
    expect(onUpload).toHaveBeenNthCalledWith(2, [secondFile]);
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("başarısız dosyayı korur ve yeniden denemeye izin verir", async () => {
    const user = userEvent.setup();
    const onUpload = vi
      .fn()
      .mockResolvedValueOnce(undefined)
      .mockRejectedValueOnce(new Error("PDF içeriği okunamadı."))
      .mockResolvedValueOnce(undefined);
    const onClose = vi.fn();
    const { container } = render(
      <UploadModal open onClose={onClose} onUpload={onUpload} />,
    );
    const goodFile = new File(["ok"], "ok.txt", {
      type: "text/plain",
    });
    const badFile = new File(["bad"], "bad.pdf", {
      type: "application/pdf",
    });

    await user.upload(getFileInput(container), [goodFile, badFile]);
    await user.click(
      screen.getByRole("button", { name: "2 dosyayı yükle" }),
    );

    expect(
      (await screen.findAllByRole("alert")).some((alert) =>
        alert.textContent?.includes("PDF içeriği okunamadı."),
      ),
    ).toBe(true);
    expect(screen.queryByText("ok.txt")).not.toBeInTheDocument();
    expect(screen.getByText("bad.pdf")).toBeVisible();
    expect(screen.getByText(/1 dosya başarıyla yüklendi/)).toBeVisible();

    await user.click(
      screen.getByRole("button", { name: "1 dosyayı tekrar dene" }),
    );

    await waitFor(() => {
      expect(onUpload).toHaveBeenCalledTimes(3);
    });
    expect(onUpload).toHaveBeenLastCalledWith([badFile]);
    expect(onClose).toHaveBeenCalledOnce();
  });
});
