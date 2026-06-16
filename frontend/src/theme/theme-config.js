/** 配色风格注册表（顺序即菜单顺序；默认 github 见 theme-boot.js） */
export const STYLES = [
  {
    id: "github",
    label: "GitHub 灰栏",
    hint: "浅灰顶栏，蓝色链接",
    swatch: ["#f6f8fa", "#0969da"],
  },
  {
    id: "slate",
    label: "石板蓝",
    hint: "蓝灰商务风",
    swatch: ["#eef2f7", "#2563eb"],
  },
  {
    id: "indigo",
    label: "经典靛蓝",
    hint: "常见技术文档配色",
    swatch: ["#e8eaf6", "#3f51b5"],
  },
  {
    id: "jade",
    label: "翡翠绿",
    hint: "清爽绿色主色",
    swatch: ["#e8f0eb", "#1f7a55"],
  },
  {
    id: "teal",
    label: "青绿运维",
    hint: "偏基础设施文档",
    swatch: ["#e0f2f1", "#00695c"],
  },
];

export const DEFAULT_STYLE = "github";
export const DEFAULT_SCHEME = "light";
