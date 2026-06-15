import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

const projectRoot = dirname(fileURLToPath(import.meta.url));
const srcRoot = resolve(projectRoot, "src");

export default defineConfig({
  root: srcRoot,
  build: {
    outDir: resolve(projectRoot, "app"),
    emptyOutDir: true,
    assetsDir: "assets",
    rollupOptions: {
      input: {
        main: resolve(srcRoot, "index.html"),
        config: resolve(srcRoot, "config.html")
      }
    }
  }
});
