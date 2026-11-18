import localFont from "next/font/local";

const devanagari = localFont({
  src: "../fonts/noto-serif-devanagari-var.woff2",
  display: "swap",
  variable: "--font-serif-deva",
  weight: "400 600",
  preload: false,
  adjustFontFallback: false,
  declarations: [{ prop: "font-family", value: "Noto Serif Devanagari" }, { prop: "unicode-range", value: "U+0900-097F, U+1CD0-1CF4, U+1CF7-1CF9, U+200C-200D, U+20A8, U+20F0, U+25CC, U+A830-A839, U+A8E0-A8FF, U+11B00-11B0A" }]
});

const bengali = localFont({
  src: "../fonts/noto-serif-bengali-var.woff2",
  display: "swap",
  variable: "--font-serif-beng",
  weight: "400 600",
  preload: false,
  adjustFontFallback: false,
  declarations: [{ prop: "font-family", value: "Noto Serif Bengali" }, { prop: "unicode-range", value: "U+0951-0952, U+0964-0965, U+0980-09FE, U+1CD0, U+1CD2, U+1CD5-1CD6, U+1CD8, U+1CE1, U+1CEA, U+1CED, U+1CF2, U+1CF5-1CF7, U+200C-200D, U+25CC, U+A8F1, U+11DF0-11DF1" }]
});

const gujarati = localFont({
  src: "../fonts/noto-serif-gujarati-var.woff2",
  display: "swap",
  variable: "--font-serif-gujr",
  weight: "400 600",
  preload: false,
  adjustFontFallback: false,
  declarations: [{ prop: "font-family", value: "Noto Serif Gujarati" }, { prop: "unicode-range", value: "U+0951-0952, U+0964-0965, U+0A80-0AFF, U+200C-200D, U+25CC, U+A830-A839" }]
});

const gurmukhi = localFont({
  src: "../fonts/noto-serif-gurmukhi-var.woff2",
  display: "swap",
  variable: "--font-serif-guru",
  weight: "400 600",
  preload: false,
  adjustFontFallback: false,
  declarations: [{ prop: "font-family", value: "Noto Serif Gurmukhi" }, { prop: "unicode-range", value: "U+0951-0952, U+0964-0965, U+0A01-0A76, U+200C-200D, U+25CC, U+262C, U+A830-A839" }]
});

const kannada = localFont({
  src: "../fonts/noto-serif-kannada-var.woff2",
  display: "swap",
  variable: "--font-serif-knda",
  weight: "400 600",
  preload: false,
  adjustFontFallback: false,
  declarations: [{ prop: "font-family", value: "Noto Serif Kannada" }, { prop: "unicode-range", value: "U+0951-0952, U+0964-0965, U+0B83, U+0C80-0CF3, U+1CD0, U+1CD2-1CD3, U+1CDA, U+1CF2, U+1CF4, U+200C-200D, U+25CC, U+A830-A835" }]
});

const malayalam = localFont({
  src: "../fonts/noto-serif-malayalam-var.woff2",
  display: "swap",
  variable: "--font-serif-mlym",
  weight: "400 600",
  preload: false,
  adjustFontFallback: false,
  declarations: [{ prop: "font-family", value: "Noto Serif Malayalam" }, { prop: "unicode-range", value: "U+0307, U+0323, U+0951-0952, U+0964-0965, U+0B83, U+0D00-0D7F, U+1CDA, U+1CF2, U+200C-200D, U+25CC, U+A830-A832" }]
});

const odia = localFont({
  src: "../fonts/noto-serif-oriya-var.woff2",
  display: "swap",
  variable: "--font-serif-orya",
  weight: "400 600",
  preload: false,
  adjustFontFallback: false,
  declarations: [{ prop: "font-family", value: "Noto Serif Oriya" }, { prop: "unicode-range", value: "U+0951-0952, U+0964-0965, U+0B01-0B77, U+1CDA, U+1CF2, U+200C-200D, U+25CC" }]
});

const tamil = localFont({
  src: "../fonts/noto-serif-tamil-var.woff2",
  display: "swap",
  variable: "--font-serif-taml",
  weight: "400 600",
  preload: false,
  adjustFontFallback: false,
  declarations: [{ prop: "font-family", value: "Noto Serif Tamil" }, { prop: "unicode-range", value: "U+0964-0965, U+0B82-0BFA, U+200C-200D, U+25CC" }]
});

const telugu = localFont({
  src: "../fonts/noto-serif-telugu-var.woff2",
  display: "swap",
  variable: "--font-serif-telu",
  weight: "400 600",
  preload: false,
  adjustFontFallback: false,
  declarations: [{ prop: "font-family", value: "Noto Serif Telugu" }, { prop: "unicode-range", value: "U+0951-0952, U+0964-0965, U+0B83, U+0C00-0C7F, U+1CD5-1CD6, U+1CD8, U+1CDA, U+1CF2, U+200C-200D, U+25CC" }]
});

const nastaliq = localFont({
  src: "../fonts/noto-nastaliq-urdu-var.woff2",
  display: "swap",
  variable: "--font-nastaliq",
  weight: "400 600",
  preload: false,
  adjustFontFallback: false,
  declarations: [{ prop: "font-family", value: "Noto Nastaliq Urdu" }, { prop: "unicode-range", value: "U+0600-06FF, U+0750-077F, U+0870-0891, U+0897-08E1, U+08E3-08FF, U+200C-200E, U+FB50-FDFF, U+FE70-FE74, U+FE76-FEFC" }]
});

const naskh = localFont({
  src: "../fonts/noto-naskh-arabic-var.woff2",
  display: "swap",
  variable: "--font-naskh",
  weight: "400 600",
  preload: false,
  adjustFontFallback: false,
  declarations: [{ prop: "font-family", value: "Noto Naskh Arabic" }, { prop: "unicode-range", value: "U+0600-06FF, U+0750-077F, U+0870-0891, U+0897-08E1, U+08E3-08FF, U+200C-200E, U+FB50-FDFF, U+FE70-FE74, U+FE76-FEFC" }]
});

export const READING_SCRIPT_FONT_VARIABLES = [devanagari, bengali, gujarati, gurmukhi, kannada, malayalam, odia, tamil, telugu, nastaliq, naskh]
  .map((font) => font.variable)
  .join(" ");
