import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import { metadata } from "./layout";

const source = readFileSync(new URL("./layout.tsx", import.meta.url), "utf-8");

describe("RootLayout", () => {
  it("imports the global stylesheet so Tailwind utilities and tokens are available", () => {
    expect(source).toContain('import "./globals.css"');
  });

  it("gives the app a title and description", () => {
    /** Without these Next emits no <title> at all: the browser tab showed
     * the deployment hostname and a shared link previewed as nothing. */
    expect(metadata.title).toContain("Steam Hidden Gems");
    expect(metadata.description).toBeTruthy();
    expect(metadata.openGraph?.title).toBeTruthy();
  });
});
