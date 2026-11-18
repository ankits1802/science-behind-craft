import localFont from "next/font/local";

const devanagari = localFont({
  src: "../fonts/noto-sans-devanagari-var.woff2",
  display: "swap",
  variable: "--font-noto-deva",
  weight: "100 900",
  preload: false,
  adjustFontFallback: false,
  declarations: [{ prop: "font-family", value: "Noto Sans Devanagari" }, { prop: "unicode-range", value: "U+0900-097F, U+1CD0-1CF4, U+1CF7-1CF9, U+200C-200D, U+20A8, U+20F0, U+25CC, U+A830-A839, U+A8E0-A8FF, U+11B00-11B0A" }]
});

const bengali = localFont({
  src: "../fonts/noto-sans-bengali-var.woff2",
  display: "swap",
  variable: "--font-noto-beng",
  weight: "100 900",
  preload: false,
  adjustFontFallback: false,
  declarations: [{ prop: "font-family", value: "Noto Sans Bengali" }, { prop: "unicode-range", value: "U+0951-0952, U+0964-0965, U+0980-09FE, U+1CD0, U+1CD2, U+1CD5-1CD6, U+1CD8, U+1CE1, U+1CEA, U+1CED, U+1CF2, U+1CF5-1CF7, U+200C-200D, U+25CC, U+A8F1, U+11DF0-11DF1" }]
});

const tamil = localFont({
  src: "../fonts/noto-sans-tamil-var.woff2",
  display: "swap",
  variable: "--font-noto-taml",
  weight: "100 900",
  preload: false,
  adjustFontFallback: false,
  declarations: [{ prop: "font-family", value: "Noto Sans Tamil" }, { prop: "unicode-range", value: "U+0964-0965, U+0B82-0BFA, U+200C-200D, U+25CC" }]
});

const telugu = localFont({
  src: "../fonts/noto-sans-telugu-var.woff2",
  display: "swap",
  variable: "--font-noto-telu",
  weight: "100 900",
  preload: false,
  adjustFontFallback: false,
  declarations: [{ prop: "font-family", value: "Noto Sans Telugu" }, { prop: "unicode-range", value: "U+0951-0952, U+0964-0965, U+0B83, U+0C00-0C7F, U+1CD5-1CD6, U+1CD8, U+1CDA, U+1CF2, U+200C-200D, U+25CC" }]
});

const gujarati = localFont({
  src: "../fonts/noto-sans-gujarati-var.woff2",
  display: "swap",
  variable: "--font-noto-gujr",
  weight: "100 900",
  preload: false,
  adjustFontFallback: false,
  declarations: [{ prop: "font-family", value: "Noto Sans Gujarati" }, { prop: "unicode-range", value: "U+0951-0952, U+0964-0965, U+0A80-0AFF, U+200C-200D, U+25CC, U+A830-A839" }]
});

const kannada = localFont({
  src: "../fonts/noto-sans-kannada-var.woff2",
  display: "swap",
  variable: "--font-noto-knda",
  weight: "100 900",
  preload: false,
  adjustFontFallback: false,
  declarations: [{ prop: "font-family", value: "Noto Sans Kannada" }, { prop: "unicode-range", value: "U+0951-0952, U+0964-0965, U+0B83, U+0C80-0CF3, U+1CD0, U+1CD2-1CD3, U+1CDA, U+1CF2, U+1CF4, U+200C-200D, U+25CC, U+A830-A835" }]
});

const malayalam = localFont({
  src: "../fonts/noto-sans-malayalam-var.woff2",
  display: "swap",
  variable: "--font-noto-mlym",
  weight: "100 900",
  preload: false,
  adjustFontFallback: false,
  declarations: [{ prop: "font-family", value: "Noto Sans Malayalam" }, { prop: "unicode-range", value: "U+0307, U+0323, U+0951-0952, U+0964-0965, U+0B83, U+0D00-0D7F, U+1CDA, U+1CF2, U+200C-200D, U+25CC, U+A830-A832" }]
});

const odia = localFont({
  src: "../fonts/noto-sans-oriya-var.woff2",
  display: "swap",
  variable: "--font-noto-orya",
  weight: "100 900",
  preload: false,
  adjustFontFallback: false,
  declarations: [{ prop: "font-family", value: "Noto Sans Oriya" }, { prop: "unicode-range", value: "U+0951-0952, U+0964-0965, U+0B01-0B77, U+1CDA, U+1CF2, U+200C-200D, U+25CC" }]
});

const gurmukhi = localFont({
  src: "../fonts/noto-sans-gurmukhi-var.woff2",
  display: "swap",
  variable: "--font-noto-guru",
  weight: "100 900",
  preload: false,
  adjustFontFallback: false,
  declarations: [{ prop: "font-family", value: "Noto Sans Gurmukhi" }, { prop: "unicode-range", value: "U+0951-0952, U+0964-0965, U+0A01-0A76, U+200C-200D, U+25CC, U+262C, U+A830-A839" }]
});

const arabic = localFont({
  src: "../fonts/noto-sans-arabic-var.woff2",
  display: "swap",
  variable: "--font-noto-arab",
  weight: "100 900",
  preload: false,
  adjustFontFallback: false,
  declarations: [{ prop: "font-family", value: "Noto Sans Arabic" }, { prop: "unicode-range", value: "U+0600-06FF, U+0750-077F, U+0870-0891, U+0897-08E1, U+08E3-08FF, U+200C-200E, U+FB50-FDFF, U+FE70-FE74, U+FE76-FEFC" }]
});

const meeteiMayek = localFont({
  src: "../fonts/noto-sans-meetei-mayek-var.woff2",
  display: "swap",
  variable: "--font-noto-mtei",
  weight: "400 600",
  preload: false,
  adjustFontFallback: false,
  declarations: [{ prop: "font-family", value: "Noto Sans Meetei Mayek" }, { prop: "unicode-range", value: "U+AAE0-AAF6, U+ABC0-ABED, U+ABF0-ABF9, U+200C-200D, U+25CC" }]
});

const olChiki = localFont({
  src: "../fonts/noto-sans-ol-chiki-var.woff2",
  display: "swap",
  variable: "--font-noto-olck",
  weight: "400 600",
  preload: false,
  adjustFontFallback: false,
  declarations: [{ prop: "font-family", value: "Noto Sans Ol Chiki" }, { prop: "unicode-range", value: "U+1C50-1C7F, U+200C-200D, U+25CC" }]
});

export const SCRIPT_FONT_VARIABLES = [devanagari, bengali, tamil, telugu, gujarati, kannada, malayalam, odia, gurmukhi, arabic, meeteiMayek, olChiki]
  .map((font) => font.variable)
  .join(" ");
