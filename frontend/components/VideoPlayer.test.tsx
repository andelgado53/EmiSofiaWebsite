import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import VideoPlayer from "./VideoPlayer";

describe("VideoPlayer", () => {
  it("renders a video element with controls and no autoplay", () => {
    render(<VideoPlayer src="https://cdn.example.com/video.mp4" />);
    const video = screen.getByLabelText("Video");
    expect(video.tagName).toBe("VIDEO");
    expect(video).toHaveAttribute("controls");
    expect(video).not.toHaveAttribute("autoplay");
  });

  it("uses the src prop as the video source", () => {
    render(<VideoPlayer src="https://cdn.example.com/test.mp4" />);
    const video = screen.getByLabelText("Video");
    expect(video).toHaveAttribute("src", "https://cdn.example.com/test.mp4");
  });

  it("uses the alt prop as aria-label", () => {
    render(<VideoPlayer src="https://cdn.example.com/video.mp4" alt="Trip video" />);
    const video = screen.getByLabelText("Trip video");
    expect(video).toBeInTheDocument();
  });

  it("applies the className prop to the video element", () => {
    render(<VideoPlayer src="https://cdn.example.com/video.mp4" className="w-full rounded" />);
    const video = screen.getByLabelText("Video");
    expect(video).toHaveClass("w-full", "rounded");
  });

  it("shows fallback message on error", () => {
    render(<VideoPlayer src="https://cdn.example.com/broken.mp4" />);
    const video = screen.getByLabelText("Video");

    fireEvent.error(video);

    expect(screen.getByText("Video unavailable")).toBeInTheDocument();
    expect(screen.queryByLabelText("Video")).not.toBeInTheDocument();
  });

  it("applies className to the fallback container on error", () => {
    render(<VideoPlayer src="https://cdn.example.com/broken.mp4" className="aspect-video" />);
    const video = screen.getByLabelText("Video");

    fireEvent.error(video);

    const fallback = screen.getByRole("alert");
    expect(fallback).toHaveClass("aspect-video");
  });

  it("uses alt prop as aria-label on fallback container", () => {
    render(<VideoPlayer src="https://cdn.example.com/broken.mp4" alt="My video" />);
    const video = screen.getByLabelText("My video");

    fireEvent.error(video);

    const fallback = screen.getByRole("alert");
    expect(fallback).toHaveAttribute("aria-label", "My video");
  });

  it("is keyboard accessible via native controls", () => {
    render(<VideoPlayer src="https://cdn.example.com/video.mp4" />);
    const video = screen.getByLabelText("Video");
    // Native video controls are focusable by default
    expect(video.tagName).toBe("VIDEO");
    expect(video).toHaveAttribute("controls");
  });
});
