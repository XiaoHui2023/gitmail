import { DEFAULT_SCHEME, DEFAULT_STYLE } from "./theme-config.js";

const STYLE_KEY = "gitmail-style";
const SCHEME_KEY = "gitmail-scheme";

export { STYLE_KEY, SCHEME_KEY };

export function readStoredTheme() {
  return {
    style: localStorage.getItem(STYLE_KEY) || DEFAULT_STYLE,
    scheme: localStorage.getItem(SCHEME_KEY) || DEFAULT_SCHEME,
  };
}

export function applyTheme(style, scheme) {
  const root = document.documentElement;
  root.dataset.appStyle = style;
  root.dataset.appScheme = scheme;
  root.dataset.appSchemeGuard = scheme;
  localStorage.setItem(STYLE_KEY, style);
  localStorage.setItem(SCHEME_KEY, scheme);
}

export function bootTheme() {
  const { style, scheme } = readStoredTheme();
  applyTheme(style, scheme);
}

bootTheme();
