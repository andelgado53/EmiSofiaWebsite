import { describe, it, expect } from "vitest";
import {
  validateMediaFile,
  resolveContentType,
  getMediaType,
  ALLOWED_TYPES,
  EXT_TO_CONTENT_TYPE,
} from "./MediaUpload";

describe("validateMediaFile", () => {
  it("accepts a valid JPEG file", () => {
    const result = validateMediaFile({ name: "photo.jpg", type: "image/jpeg", size: 5 * 1024 * 1024 });
    expect(result.valid).toBe(true);
    expect(result.contentType).toBe("image/jpeg");
  });

  it("accepts a valid PNG file", () => {
    const result = validateMediaFile({ name: "photo.png", type: "image/png", size: 1024 });
    expect(result.valid).toBe(true);
    expect(result.contentType).toBe("image/png");
  });

  it("accepts a valid MP4 video file", () => {
    const result = validateMediaFile({ name: "video.mp4", type: "video/mp4", size: 50 * 1024 * 1024 });
    expect(result.valid).toBe(true);
    expect(result.contentType).toBe("video/mp4");
  });

  it("accepts a valid WebM video file", () => {
    const result = validateMediaFile({ name: "video.webm", type: "video/webm", size: 80 * 1024 * 1024 });
    expect(result.valid).toBe(true);
    expect(result.contentType).toBe("video/webm");
  });

  it("rejects a 0-byte file", () => {
    const result = validateMediaFile({ name: "empty.jpg", type: "image/jpeg", size: 0 });
    expect(result.valid).toBe(false);
    expect(result.error).toBe("File is empty.");
  });

  it("rejects an unsupported file type", () => {
    const result = validateMediaFile({ name: "doc.pdf", type: "application/pdf", size: 1024 });
    expect(result.valid).toBe(false);
    expect(result.error).toBe("Only JPEG, PNG, MP4, and WebM files are accepted.");
  });

  it("rejects a photo exceeding 10 MB", () => {
    const result = validateMediaFile({ name: "big.jpg", type: "image/jpeg", size: 11 * 1024 * 1024 });
    expect(result.valid).toBe(false);
    expect(result.error).toBe("Photo file size must be 10 MB or less.");
  });

  it("rejects a video exceeding 100 MB", () => {
    const result = validateMediaFile({ name: "big.mp4", type: "video/mp4", size: 101 * 1024 * 1024 });
    expect(result.valid).toBe(false);
    expect(result.error).toBe("Video file size must be 100 MB or less.");
  });

  it("falls back to extension when MIME type is empty", () => {
    const result = validateMediaFile({ name: "video.mp4", type: "", size: 5 * 1024 * 1024 });
    expect(result.valid).toBe(true);
    expect(result.contentType).toBe("video/mp4");
  });

  it("rejects unknown extension when MIME type is empty", () => {
    const result = validateMediaFile({ name: "file.xyz", type: "", size: 1024 });
    expect(result.valid).toBe(false);
    expect(result.error).toBe("Only JPEG, PNG, MP4, and WebM files are accepted.");
  });
});

describe("resolveContentType", () => {
  it("returns MIME type when it is a known allowed type", () => {
    expect(resolveContentType({ name: "test.jpg", type: "image/jpeg" })).toBe("image/jpeg");
    expect(resolveContentType({ name: "test.mp4", type: "video/mp4" })).toBe("video/mp4");
  });

  it("falls back to extension for empty MIME type", () => {
    expect(resolveContentType({ name: "test.webm", type: "" })).toBe("video/webm");
    expect(resolveContentType({ name: "test.jpeg", type: "" })).toBe("image/jpeg");
    expect(resolveContentType({ name: "test.png", type: "" })).toBe("image/png");
  });

  it("returns null for unknown type and extension", () => {
    expect(resolveContentType({ name: "test.gif", type: "image/gif" })).toBeNull();
    expect(resolveContentType({ name: "test.txt", type: "" })).toBeNull();
  });
});

describe("getMediaType", () => {
  it("returns 'video' for video content types", () => {
    expect(getMediaType("video/mp4")).toBe("video");
    expect(getMediaType("video/webm")).toBe("video");
  });

  it("returns 'photo' for image content types", () => {
    expect(getMediaType("image/jpeg")).toBe("photo");
    expect(getMediaType("image/png")).toBe("photo");
  });
});

describe("ALLOWED_TYPES", () => {
  it("has correct max sizes", () => {
    expect(ALLOWED_TYPES["image/jpeg"].maxSize).toBe(10 * 1024 * 1024);
    expect(ALLOWED_TYPES["image/png"].maxSize).toBe(10 * 1024 * 1024);
    expect(ALLOWED_TYPES["video/mp4"].maxSize).toBe(100 * 1024 * 1024);
    expect(ALLOWED_TYPES["video/webm"].maxSize).toBe(100 * 1024 * 1024);
  });
});

describe("EXT_TO_CONTENT_TYPE", () => {
  it("maps extensions to correct content types", () => {
    expect(EXT_TO_CONTENT_TYPE["mp4"]).toBe("video/mp4");
    expect(EXT_TO_CONTENT_TYPE["webm"]).toBe("video/webm");
    expect(EXT_TO_CONTENT_TYPE["jpg"]).toBe("image/jpeg");
    expect(EXT_TO_CONTENT_TYPE["jpeg"]).toBe("image/jpeg");
    expect(EXT_TO_CONTENT_TYPE["png"]).toBe("image/png");
  });
});
