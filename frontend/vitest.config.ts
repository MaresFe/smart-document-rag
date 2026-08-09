import { defineConfig } from "vitest/config";


export default defineConfig({
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    setupFiles: ["./src/test/setup.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text"],
      include: [
        "src/services/**/*.ts",
        "src/components/AuthScreen.tsx",
        "src/components/InvitationAcceptScreen.tsx",
        "src/components/ForgotPasswordScreen.tsx",
        "src/components/PasswordResetScreen.tsx",
        "src/components/AdminUserPanel.tsx",
        "src/components/WorkspaceDialog.tsx",
        "src/components/UploadModal.tsx",
      ],
    },
  },
});
