import { defineConfig } from "vitest/config";


export default defineConfig({
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    coverage: {
      provider: "v8",
      reporter: ["text"],
      include: ["src/services/**/*.ts"],
      exclude: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    },
  },
});
