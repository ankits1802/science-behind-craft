import { expect, test } from "@playwright/test";

import { decimalsOf, formatMeasure, formatNumber, formatRange, measureParts } from "@/lib/measure";

test("units read as people write them", () => {
  expect(formatMeasure(8.1, "pH")).toBe("pH 8.1");
  expect(formatMeasure(26.6, "degC")).toBe("26.6 °C");
  expect(formatMeasure(0.236, "fraction")).toBe("23.6%");
  expect(formatMeasure(0.3, "fraction of annual")).toBe("30% of annual");
  expect(formatMeasure(27.4, "%")).toBe("27.4%");
  expect(formatMeasure(1.5, "m3/s")).toBe("1.5 m³/s");
  expect(formatMeasure(0.8, "km/km2")).toBe("0.8 km/km²");
  expect(measureParts("")).toEqual({ prefix: "", suffix: "", scale: 1 });
});

test("numbers keep at most two decimals and use Indian grouping", () => {
  expect(decimalsOf(8)).toBe(0);
  expect(decimalsOf(7.25)).toBe(2);
  expect(decimalsOf(0.123456)).toBe(2);
  expect(formatNumber(123456)).toBe("1,23,456");
  expect(formatNumber(-57.3)).toBe("−57.3");
  expect(() => decimalsOf(Number.NaN)).toThrow(RangeError);
});

test("ranges share their decimals and say open ends", () => {
  expect(formatRange(6.4, 7, "pH")).toBe("pH 6.4–7.0");
  expect(formatRange(240, 360, "h")).toBe("240–360 h");
  expect(formatRange(336, 336, "h")).toBe("336 h");
  expect(formatRange(null, 4, "h")).toBe("≤ 4 h");
  expect(formatRange(60, null, "°C")).toBe("≥ 60 °C");
  expect(formatRange(0.2, 0.35, "fraction")).toBe("20–35%");
  expect(formatRange(null, null, "g/L")).toBeNull();
});

test("a p-value reads with its significance and never as zero", () => {
  expect(formatMeasure(0.0000123, "p-value")).toBe("p < 0.001");
  expect(formatMeasure(0.0046, "p-value")).toBe("p = 0.005");
  expect(formatMeasure(0.049, "p-value")).toBe("p = 0.049");
  expect(formatMeasure(0.12, "p-value")).toBe("p = 0.12");
});

test("soil, terrain, river and rainfall units read as people write them", () => {
  expect(formatMeasure(1.45, "kg/dm3")).toBe("1.45 g/cm³");
  expect(formatMeasure(0.74, "degree")).toBe("0.74°");
  expect(formatMeasure(6, "Strahler order")).toBe("6");
  expect(formatMeasure(145.4, "coefficient of variation %")).toBe("145.4%");
});
