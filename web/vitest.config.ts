import { defineConfig, defineProject } from "vitest/config";

export default defineConfig({
  esbuild: {
    jsx: "automatic",
  },
  test: {
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
  },
  projects: [
    defineProject({
      name: "unit",
      test: {
        environment: "node",
        include: ["**/*.test.ts"],
      },
    }),
    defineProject({
      name: "components",
      test: {
        environment: "jsdom",
        setupFiles: ["./vitest.setup.ts"],
        include: ["**/*.test.tsx"],
      },
    }),
  ],
});
