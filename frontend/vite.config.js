import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/auth": "http://127.0.0.1:8000",
      "/certificates": "http://127.0.0.1:8000",
      "/clubs": "http://127.0.0.1:8000",
      "/issue": "http://127.0.0.1:8000",
      "/templates": "http://127.0.0.1:8000",
      "/issuances": "http://127.0.0.1:8000",
      "/assets": "http://127.0.0.1:8000",
      "/verify": "http://127.0.0.1:8000",
    },
  },
});
