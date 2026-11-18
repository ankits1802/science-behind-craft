import plugin from "tailwindcss/plugin";

type Token = (name: string) => string;

const SHADES = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950] as const;

export const APPEARANCE_RAMPS = {
  "purple-fill": ["map-land", "map-land", "density-1", "density-1", "density-2", "density-3", "density-4", "density-5", "density-6", "density-6", "density-6"],
  "purple-stroke": ["map-border-district", "map-border-district", "map-border-district", "map-coast", "map-coast", "map-border-intl", "map-border-intl", "map-selection", "map-selection", "map-selection", "map-selection"],
  errand: ["map-water", "map-water", "rain-1", "rain-2", "map-river", "map-river", "series-rain", "series-rain", "map-water-label", "map-water-label", "map-water-label"],
  steward: ["error-wash", "error-wash", "heat-1", "heat-2", "heat-3", "heat-4", "series-heat", "series-heat", "error", "error", "error"],
  archive: ["map-water", "map-water", "map-water", "map-river", "map-river", "map-river", "map-water-label", "map-water-label", "map-water-label", "map-water-label", "map-water-label"]
} as const;

type AppearanceRamp = keyof typeof APPEARANCE_RAMPS;

export const DARK_APPEARANCE_RAMPS: Partial<Record<AppearanceRamp, readonly string[]>> = {
  "purple-fill": ["density-6", "density-6", "density-6", "density-5", "density-5", "density-4", "density-3", "density-2", "density-1", "map-land", "map-land"]
};

const REACTION_DYES = {
  red: "oklch(0.52 0.17 27 / <alpha-value>)",
  blue: "oklch(0.42 0.14 262 / <alpha-value>)",
  black: "oklch(0.24 0.012 60 / <alpha-value>)",
  white: "oklch(0.97 0.012 90 / <alpha-value>)",
  green: "oklch(0.64 0.15 142 / <alpha-value>)",
  yellow: "oklch(0.86 0.15 95 / <alpha-value>)",
  brown: "oklch(0.43 0.08 55 / <alpha-value>)",
  grey: "oklch(0.63 0.01 260 / <alpha-value>)",
  pink: "oklch(0.79 0.11 0 / <alpha-value>)",
  purple: "oklch(0.46 0.16 312 / <alpha-value>)",
  orange: "oklch(0.71 0.16 55 / <alpha-value>)",
  maroon: "oklch(0.36 0.12 15 / <alpha-value>)"
};

function byShade(c: Token, names: readonly string[]): Record<number, string> {
  return Object.fromEntries(SHADES.map((shade, index) => [shade, c(names[index])]));
}

function oneShade(value: string): Record<number, string> {
  return Object.fromEntries(SHADES.map((shade) => [shade, value]));
}

function tinted(c: Token, strong: string, wash: string): Record<number, string> {
  return byShade(c, [wash, wash, wash, strong, strong, strong, strong, strong, wash, wash, wash]);
}

function appearance(ramp: AppearanceRamp): Record<number, string> {
  return Object.fromEntries(SHADES.map((shade) => [shade, `var(--legacy-${ramp}-${shade})`]));
}

export function legacyRampToken(ramp: AppearanceRamp, shade: (typeof SHADES)[number], theme: "light" | "dark"): string {
  const index = SHADES.indexOf(shade);
  if (theme === "light") return APPEARANCE_RAMPS[ramp][index];
  return DARK_APPEARANCE_RAMPS[ramp]?.[index] ?? APPEARANCE_RAMPS[ramp][SHADES.length - 1 - index];
}

function appearanceVariables(theme: "light" | "dark"): Record<string, string> {
  return Object.fromEntries(
    (Object.keys(APPEARANCE_RAMPS) as AppearanceRamp[]).flatMap((ramp) => SHADES.map((shade) => [`--legacy-${ramp}-${shade}`, `var(--${legacyRampToken(ramp, shade, theme)})`]))
  );
}

export const appearanceRamps = plugin(({ addBase }) => {
  addBase({
    ":root": appearanceVariables("light"),
    ':root[data-theme="dark"]': appearanceVariables("dark")
  });
});

export function retiredColors(c: Token) {
  return {
    field: { 50: c("sunk"), 100: c("sunk"), 200: c("sunk"), 300: c("rule"), 400: c("indigo"), 500: c("indigo"), 600: c("indigo"), 700: c("indigo-hover"), 900: c("ink-1") },
    gold: tinted(c, "turmeric", "turmeric-wash"),
    evidence: tinted(c, "success", "success-wash"),
    emerald: tinted(c, "success", "success-wash"),
    amber: tinted(c, "warning", "warning-wash"),
    red: byShade(c, ["error-wash", "error-wash", "error-wash", "error", "error", "error", "error", "madder", "error-wash", "error-wash", "error-wash"]),
    errand: appearance("errand"),
    steward: appearance("steward"),
    archive: appearance("archive"),
    dye: REACTION_DYES,
    black: "rgb(0 0 0 / <alpha-value>)"
  };
}

export function retiredUtilityColors(c: Token) {
  const indigo = oneShade(c("indigo"));
  return {
    textColor: {
      purple: byShade(c, ["on-indigo", "ink-2", "indigo-hover", "indigo", "indigo", "indigo", "indigo", "indigo", "indigo-hover", "indigo-hover", "on-indigo"]),
      gold: oneShade(c("turmeric-text")),
      evidence: oneShade(c("success")),
      emerald: oneShade(c("success")),
      amber: oneShade(c("warning")),
      red: oneShade(c("error")),
      white: c("on-indigo")
    },
    backgroundColor: {
      purple: byShade(c, ["sunk", "sunk", "turmeric-wash", "indigo", "indigo", "indigo", "indigo", "indigo", "indigo-hover", "sunk", "sunk"])
    },
    borderColor: {
      purple: byShade(c, ["rule-strong", "rule-strong", "rule-strong", "rule-strong", "indigo", "indigo", "indigo", "indigo", "rule-strong", "rule-strong", "rule-strong"]),
      evidence: oneShade(c("success")),
      emerald: oneShade(c("success")),
      amber: oneShade(c("warning")),
      red: oneShade(c("error"))
    },
    ringColor: {
      purple: byShade(c, ["indigo-wash", "indigo-wash", "indigo-wash", "indigo", "indigo", "indigo", "indigo", "indigo", "indigo-wash", "indigo-wash", "indigo-wash"])
    },
    outlineColor: { purple: indigo },
    accentColor: { purple: indigo },
    caretColor: { purple: indigo },
    textDecorationColor: { purple: indigo },
    fill: { purple: appearance("purple-fill") },
    stroke: { purple: appearance("purple-stroke") }
  };
}
