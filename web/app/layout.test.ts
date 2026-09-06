import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(new URL("./layout.tsx", import.meta.url), "utf-8");

describe("RootLayout", () => {
  it("imports the global stylesheet so Tailwind utilities and tokens are available", () => {
    expect(source).toContain('import "./globals.css"');
  });
});
