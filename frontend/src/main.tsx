import React from "react";
import ReactDOM from "react-dom/client";

import App from "@/App";
import { useThemeStore } from "@/stores/themeStore";
import "@/styles/globals.css";

useThemeStore.getState().initialize();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
