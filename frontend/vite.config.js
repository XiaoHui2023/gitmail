import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "./",
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8765",
        changeOrigin: true,
        configure(proxy) {
          proxy.on("proxyReq", (proxyReq, req) => {
            const remote = req.socket?.remoteAddress ?? req.connection?.remoteAddress;
            if (remote) {
              const clientIp = remote.startsWith("::ffff:") ? remote.slice(7) : remote;
              proxyReq.setHeader("X-Forwarded-For", clientIp);
            }
          });
        },
      },
    },
  },
});
