import { NavLink, Route, Routes } from "react-router-dom";

import { CasePage } from "./case-page/CasePage";
import { DebatePage } from "./debate-page/DebatePage";
import { ResolutionPage } from "./resolution-page/ResolutionPage";

const navItems = [
  { to: "/", label: "Case" },
  { to: "/debate", label: "Debate" },
  { to: "/resolution", label: "Resolution" },
];

export default function App() {
  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">ETH Beijing Hackathon</p>
          <h1>Human-AI Jury</h1>
          <p className="hero-copy">
            A transparent digital court for disputed events. Investigation agents
            gather evidence, adversarial agents debate it, humans challenge the
            arguments, and the final verdict can be recorded on Sepolia.
          </p>
        </div>
        <nav className="top-nav" aria-label="Primary">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>

      <main className="main-grid">
        <Routes>
          <Route path="/" element={<CasePage />} />
          <Route path="/debate" element={<DebatePage />} />
          <Route path="/resolution" element={<ResolutionPage />} />
        </Routes>
      </main>
    </div>
  );
}
