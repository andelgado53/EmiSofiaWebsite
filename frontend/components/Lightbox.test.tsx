import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import Lightbox from "./Lightbox";

const mockPhotos = [
  { cdn_url: "https://cdn.example.com/photo1.jpg", position: 1 },
  { cdn_url: "https://cdn.example.com/photo2.jpg", position: 2 },
  { cdn_url: "https://cdn.example.com/photo3.jpg", position: 3 },
];

describe("Lightbox", () => {
  it("renders a modal overlay with dark backdrop", () => {
    render(<Lightbox photos={mockPhotos} initialIndex={0} onClose={() => {}} />);
    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveClass("bg-black/80");
  });

  it("displays the selected photo at the initial index", () => {
    render(<Lightbox photos={mockPhotos} initialIndex={1} onClose={() => {}} />);
    const img = screen.getByRole("img");
    expect(img).toHaveAttribute("src", "https://cdn.example.com/photo2.jpg");
    expect(img).toHaveAttribute("alt", "Photo 2 of 3");
  });

  it("navigates to next photo when clicking next button", async () => {
    const user = userEvent.setup();
    render(<Lightbox photos={mockPhotos} initialIndex={0} onClose={() => {}} />);

    await user.click(screen.getByLabelText("Next photo"));

    const img = screen.getByRole("img");
    expect(img).toHaveAttribute("src", "https://cdn.example.com/photo2.jpg");
  });

  it("navigates to previous photo when clicking previous button", async () => {
    const user = userEvent.setup();
    render(<Lightbox photos={mockPhotos} initialIndex={1} onClose={() => {}} />);

    await user.click(screen.getByLabelText("Previous photo"));

    const img = screen.getByRole("img");
    expect(img).toHaveAttribute("src", "https://cdn.example.com/photo1.jpg");
  });

  it("wraps to first photo when navigating next from last", async () => {
    const user = userEvent.setup();
    render(<Lightbox photos={mockPhotos} initialIndex={2} onClose={() => {}} />);

    await user.click(screen.getByLabelText("Next photo"));

    const img = screen.getByRole("img");
    expect(img).toHaveAttribute("src", "https://cdn.example.com/photo1.jpg");
  });

  it("wraps to last photo when navigating previous from first", async () => {
    const user = userEvent.setup();
    render(<Lightbox photos={mockPhotos} initialIndex={0} onClose={() => {}} />);

    await user.click(screen.getByLabelText("Previous photo"));

    const img = screen.getByRole("img");
    expect(img).toHaveAttribute("src", "https://cdn.example.com/photo3.jpg");
  });

  it("closes when clicking the close button", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<Lightbox photos={mockPhotos} initialIndex={0} onClose={onClose} />);

    await user.click(screen.getByLabelText("Close lightbox"));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("closes when pressing Escape key", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<Lightbox photos={mockPhotos} initialIndex={0} onClose={onClose} />);

    await user.keyboard("{Escape}");

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("navigates next when pressing right arrow key", async () => {
    const user = userEvent.setup();
    render(<Lightbox photos={mockPhotos} initialIndex={0} onClose={() => {}} />);

    await user.keyboard("{ArrowRight}");

    const img = screen.getByRole("img");
    expect(img).toHaveAttribute("src", "https://cdn.example.com/photo2.jpg");
  });

  it("navigates previous when pressing left arrow key", async () => {
    const user = userEvent.setup();
    render(<Lightbox photos={mockPhotos} initialIndex={2} onClose={() => {}} />);

    await user.keyboard("{ArrowLeft}");

    const img = screen.getByRole("img");
    expect(img).toHaveAttribute("src", "https://cdn.example.com/photo2.jpg");
  });

  it("closes when clicking the backdrop", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<Lightbox photos={mockPhotos} initialIndex={0} onClose={onClose} />);

    await user.click(screen.getByRole("dialog"));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("does not close when clicking the photo itself", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<Lightbox photos={mockPhotos} initialIndex={0} onClose={onClose} />);

    await user.click(screen.getByRole("img"));

    expect(onClose).not.toHaveBeenCalled();
  });

  it("prevents body scroll while open", () => {
    render(<Lightbox photos={mockPhotos} initialIndex={0} onClose={() => {}} />);
    expect(document.body.style.overflow).toBe("hidden");
  });

  it("restores body scroll on unmount", () => {
    document.body.style.overflow = "auto";
    const { unmount } = render(
      <Lightbox photos={mockPhotos} initialIndex={0} onClose={() => {}} />
    );
    expect(document.body.style.overflow).toBe("hidden");

    unmount();
    expect(document.body.style.overflow).toBe("auto");
  });
});
