import { useState } from "react";
import { applyTheme, readStoredTheme } from "../theme/theme-boot.js";

const STYLES = [
  { id: "jade", label: "翡翠" },
  { id: "slate", label: "石板" },
];

export default function ThemeBar() {
  const [theme, setTheme] = useState(readStoredTheme);

  function setStyle(style) {
    applyTheme(style, theme.scheme);
    setTheme(readStoredTheme());
  }

  function toggleScheme() {
    const next = theme.scheme === "dark" ? "light" : "dark";
    applyTheme(theme.style, next);
    setTheme(readStoredTheme());
  }

  return (
    <header className="app-chrome">
      <div className="app-brand">gitmail</div>
      <div className="theme-controls">
        <select
          aria-label="配色风格"
          value={theme.style}
          onChange={(e) => setStyle(e.target.value)}
        >
          {STYLES.map((s) => (
            <option key={s.id} value={s.id}>
              {s.label}
            </option>
          ))}
        </select>
        <button type="button" aria-label="切换明暗" onClick={toggleScheme}>
          {theme.scheme === "dark" ? "浅色" : "深色"}
        </button>
      </div>
    </header>
  );
}
