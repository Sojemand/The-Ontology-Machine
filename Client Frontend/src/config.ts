import "./styles/main.css";

import { createConfigApp } from "./config_app.ts";

const app = createConfigApp();

void app.boot().catch((error) => {
  app.setSaveStatus(
    error instanceof Error ? error.message : "Configuration could not be loaded.",
    "error"
  );
});
