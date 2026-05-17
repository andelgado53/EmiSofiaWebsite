import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import LabelInput from "./LabelInput";

describe("LabelInput", () => {
  it("renders existing labels as chips", () => {
    render(<LabelInput labels={["life", "lessons"]} onLabelsChange={() => {}} />);
    expect(screen.getByText("life")).toBeInTheDocument();
    expect(screen.getByText("lessons")).toBeInTheDocument();
  });

  it("adds a label when clicking Add", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<LabelInput labels={[]} onLabelsChange={onChange} />);

    await user.type(screen.getByLabelText("Label input"), "new-label");
    await user.click(screen.getByRole("button", { name: "Add" }));

    expect(onChange).toHaveBeenCalledWith(["new-label"]);
  });

  it("adds a label when pressing Enter", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<LabelInput labels={[]} onLabelsChange={onChange} />);

    const input = screen.getByLabelText("Label input");
    await user.type(input, "enter-label{Enter}");

    expect(onChange).toHaveBeenCalledWith(["enter-label"]);
  });

  it("shows error for empty label", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<LabelInput labels={[]} onLabelsChange={onChange} />);

    await user.click(screen.getByRole("button", { name: "Add" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Label cannot be empty.");
    expect(onChange).not.toHaveBeenCalled();
  });

  it("shows error for label exceeding 50 characters", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<LabelInput labels={[]} onLabelsChange={onChange} />);

    const longLabel = "a".repeat(51);
    await user.type(screen.getByLabelText("Label input"), longLabel);
    await user.click(screen.getByRole("button", { name: "Add" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Label must be 50 characters or fewer");
    expect(onChange).not.toHaveBeenCalled();
  });

  it("shows warning for case-insensitive duplicate", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<LabelInput labels={["Life"]} onLabelsChange={onChange} />);

    await user.type(screen.getByLabelText("Label input"), "life");
    await user.click(screen.getByRole("button", { name: "Add" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      '"life" already exists (case-insensitive match).'
    );
    expect(onChange).not.toHaveBeenCalled();
  });

  it("removes a label when clicking X", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<LabelInput labels={["one", "two", "three"]} onLabelsChange={onChange} />);

    await user.click(screen.getByLabelText("Remove label two"));

    expect(onChange).toHaveBeenCalledWith(["one", "three"]);
  });

  it("disables input and Add button at 20 labels", () => {
    const labels = Array.from({ length: 20 }, (_, i) => `label-${i}`);
    render(<LabelInput labels={labels} onLabelsChange={() => {}} />);

    expect(screen.getByLabelText("Label input")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Add" })).toBeDisabled();
  });

  it("shows the label count", () => {
    render(<LabelInput labels={["a", "b"]} onLabelsChange={() => {}} />);
    expect(screen.getByText("Labels (2/20)")).toBeInTheDocument();
  });
});
