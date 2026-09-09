import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import tsConfigPaths from "vite-tsconfig-paths";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";

// NOTE: Do NOT add TanStackRouterVite here.
// @tanstack/react-start already includes TanStack Router plugin internally
// with the correct SSR-compatible configuration.
// Adding TanStackRouterVite separately with autoCodeSplitting creates a
// conflict where TSRSplitComponent stubs get injected but the SSR module
// runner cannot resolve them, causing a ReferenceError at runtime.

export default defineConfig({
  plugins: [
    tsConfigPaths({ projects: ["./tsconfig.json"] }),
    tanstackStart({
      // Redirect TanStack Start's bundled server entry to src/server.ts (our SSR error wrapper).
      server: { entry: "server" },
    }),
    react(),
    tailwindcss(),
  ],
  server: {
    port: 8080,
    host: true,
  },
});
