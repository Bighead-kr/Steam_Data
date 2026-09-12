import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ErrorState } from "./ErrorState";

describe("ErrorState", () => {
  it("announces the failure and shows the reason", () => {
    render(<ErrorState message="서버가 503 오류를 반환했습니다." />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("결과를 불러오지 못했습니다")).toBeInTheDocument();
    expect(screen.getByText("서버가 503 오류를 반환했습니다.")).toBeInTheDocument();
  });

  it("offers a retry when one is available", () => {
    const onRetry = vi.fn();
    render(<ErrorState message="…" onRetry={onRetry} />);
    fireEvent.click(screen.getByRole("button", { name: "다시 시도" }));
    expect(onRetry).toHaveBeenCalled();
  });
});
