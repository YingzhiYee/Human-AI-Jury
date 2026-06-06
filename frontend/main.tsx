import React from "react";
import ReactDOM from "react-dom/client";
import { HashRouter } from "react-router-dom";

import App from "./App";
import { SessionProvider } from "./lib/session";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <SessionProvider>
      <HashRouter>
        <App />
      </HashRouter>
    </SessionProvider>
  </React.StrictMode>,
);
