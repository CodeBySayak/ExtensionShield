import React, { useState, useRef } from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within, fireEvent } from "@testing-library/react";
import DemoModal from "../DemoModal";

function TestWrapper() {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef(null);
  return (
    <>
      <button type="button" ref={triggerRef} onClick={() => setOpen(true)}>
        Watch demo
      </button>
      <DemoModal isOpen={open} onClose={() => setOpen(false)} triggerRef={triggerRef} />
    </>
  );
}

describe("DemoModal", () => {
  beforeEach(() => {
    vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() })));
  });

  it("opens on Watch demo click, shows step 1 image; Next twice shows step 3; Done closes", () => {
    render(<TestWrapper />);

    const watchDemoBtn = screen.getByRole("button", { name: /watch demo/i });
    fireEvent.click(watchDemoBtn);

    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();

    const img = within(dialog).getByRole("img", { hidden: true });
    expect(img).toHaveAttribute("src", expect.stringContaining("demo-step1"));

    const nextBtn = within(dialog).getByRole("button", { name: /next/i });
    fireEvent.click(nextBtn);
    expect(within(dialog).getByRole("img", { hidden: true })).toHaveAttribute("src", expect.stringContaining("demo-step2"));

    fireEvent.click(nextBtn);
    expect(within(dialog).getByRole("img", { hidden: true })).toHaveAttribute("src", expect.stringContaining("demo-step3"));

    const doneBtn = within(dialog).getByRole("button", { name: /done/i });
    fireEvent.click(doneBtn);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
