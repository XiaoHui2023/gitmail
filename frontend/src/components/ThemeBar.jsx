import { useEffect, useRef, useState } from "react";
import { applyTheme, readStoredTheme } from "../theme/theme-boot.js";
import { STYLES } from "../theme/theme-config.js";
import GitMailLogo from "./GitMailLogo.jsx";

function IconButton({ label, pressed, onClick, children }) {
  return (
    <button
      type="button"
      className="icon-btn"
      aria-label={label}
      aria-pressed={pressed}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

function PaletteIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path
        fill="currentColor"
        d="M12 3a9 9 0 1 0 8.2 12.7c-.4.7-1.2 1.1-2 1.1h-1.4c-.8 0-1.5.7-1.5 1.5V20a1 1 0 0 1-1 1 9 9 0 0 1-1-18Zm-4.5 9a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3Zm3-4.5a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3Zm6 0a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3Zm3 4.5a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3Z"
      />
    </svg>
  );
}

function SunIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path
        fill="currentColor"
        d="M12 18a6 6 0 1 0 0-12 6 6 0 0 0 0 12Zm0 4a1 1 0 0 1-1-1v-1.1a1 1 0 1 1 2 0V21a1 1 0 0 1-1 1Zm0-18a1 1 0 0 1-1-1V1a1 1 0 1 1 2 0v1.9a1 1 0 0 1-1 1ZM4.2 4.2a1 1 0 0 1 1.4 0l.8.8a1 1 0 1 1-1.4 1.4l-.8-.8a1 1 0 0 1 0-1.4Zm14.6 0a1 1 0 0 1 0 1.4l-.8.8a1 1 0 0 1-1.4-1.4l.8-.8a1 1 0 0 1 1.4 0ZM1 13a1 1 0 1 1 0-2h1.9a1 1 0 1 1 0 2H1Zm19.1 0a1 1 0 1 1 0-2H22a1 1 0 1 1 0 2h-1.9ZM4.2 19.8a1 1 0 0 1 0-1.4l.8-.8a1 1 0 1 1 1.4 1.4l-.8.8a1 1 0 0 1-1.4 0Zm14.6 0a1 1 0 0 1 1.4 0l.8.8a1 1 0 0 1-1.4 1.4l-.8-.8a1 1 0 0 1 0-1.4Z"
      />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path
        fill="currentColor"
        d="M21 14.5A8.5 8.5 0 0 1 9.5 3 7 7 0 1 0 21 14.5Z"
      />
    </svg>
  );
}

export default function ThemeBar() {
  const [theme, setTheme] = useState(readStoredTheme);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    if (!menuOpen) return undefined;

    function onPointerDown(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setMenuOpen(false);
      }
    }

    function onKeyDown(event) {
      if (event.key === "Escape") setMenuOpen(false);
    }

    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [menuOpen]);

  function setStyle(style) {
    applyTheme(style, theme.scheme);
    setTheme(readStoredTheme());
    setMenuOpen(false);
  }

  function toggleScheme() {
    const next = theme.scheme === "dark" ? "light" : "dark";
    applyTheme(theme.style, next);
    setTheme(readStoredTheme());
  }

  const activeStyle = STYLES.find((s) => s.id === theme.style) ?? STYLES[0];

  return (
    <header className="app-chrome">
      <GitMailLogo />
      <div className="theme-controls">
        <div className="style-picker" ref={menuRef}>
          <IconButton
            label={`配色风格：${activeStyle.label}`}
            pressed={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
          >
            <PaletteIcon />
          </IconButton>
          {menuOpen ? (
            <div className="style-menu" role="menu" aria-label="配色风格">
              {STYLES.map((style) => (
                <button
                  key={style.id}
                  type="button"
                  role="menuitemradio"
                  className="style-option"
                  aria-checked={theme.style === style.id}
                  title={`${style.label}：${style.hint}`}
                  onClick={() => setStyle(style.id)}
                >
                  <span className="style-swatch" aria-hidden="true">
                    <span style={{ background: style.swatch[0] }} />
                    <span style={{ background: style.swatch[1] }} />
                  </span>
                </button>
              ))}
            </div>
          ) : null}
        </div>
        <IconButton
          label={theme.scheme === "dark" ? "切换到浅色" : "切换到深色"}
          onClick={toggleScheme}
        >
          {theme.scheme === "dark" ? <SunIcon /> : <MoonIcon />}
        </IconButton>
      </div>
    </header>
  );
}
