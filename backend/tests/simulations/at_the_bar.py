from __future__ import annotations

import hashlib

__all__ = ["IRON_AT_THE_BAR", "KUT_AT_THE_BAR", "WATER_AT_THE_BAR", "at_the_bar"]

DESIGN = (
    ".kv{display:grid;gap:12px;padding:16px;font:14px/1.5 var(--font-ui);color:var(--ink-1);"
    "background:var(--sunk)}\n"
)
CHIPS = (
    ".kv .row{display:flex;flex-wrap:wrap;gap:8px}\n"
    ".kv .chip{padding:4px 8px;border:1px solid var(--rule-strong);background:var(--raised)}\n"
    ".kv .chip.on{border-color:var(--ink-1)}\n"
    ".kv button{font:14px/1.5 var(--font-ui);color:var(--indigo);background:var(--raised);"
    "border:1px solid var(--rule-strong)}\n"
)
WATER_AT_THE_BAR = (
    "<style>\n"
    f"{DESIGN}"
    ".kv label{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;align-items:center;"
    "font-size:13px;color:var(--ink-2)}\n"
    ".kv input{width:100%;accent-color:var(--indigo)}\n"
    ".kv .bar{height:16px;border:1px solid var(--rule-strong);background:var(--raised);overflow:hidden}\n"
    ".kv .fill{height:100%;width:0;background:var(--chart-series);transition:width .3s ease}\n"
    ".kv .fill.high{background:var(--chart-emph)}\n"
    "</style>\n"
    '<div class="kv">\n'
    '<label for="years">Years from now <output id="count"></output></label>\n'
    '<input id="years" type="range" min="1" max="10" step="1" value="1">\n'
    '<div class="bar" role="img" aria-label="Fall at the lower stated rate"><div class="fill" id="low"></div></div>\n'
    '<div class="bar" role="img" aria-label="Fall at the higher stated rate"><div class="fill high" id="high"></div></div>\n'
    '<p id="said" aria-live="polite"></p>\n'
    "</div>\n"
    "<script>\n"
    'const data = JSON.parse(document.getElementById("kv-data").textContent);\n'
    'const years = document.getElementById("years");\n'
    "function draw() {\n"
    "  const n = Number(years.value);\n"
    "  const most = Number(years.max) * data.fallHighFeet;\n"
    '  document.getElementById("count").textContent = String(n);\n'
    '  document.getElementById("low").style.width = (n * data.fallLowFeet / most * 100) + "%";\n'
    '  document.getElementById("high").style.width = (n * data.fallHighFeet / most * 100) + "%";\n'
    '  document.getElementById("said").textContent = "The water table is " + n * data.fallLowFeet + " to " '
    '+ n * data.fallHighFeet + " feet lower.";\n'
    "}\n"
    'years.addEventListener("input", draw);\n'
    "draw();\n"
    "</script>"
)
STEPPER = (
    "let shown = 0;\n"
    "let timer = null;\n"
    'const still = document.documentElement.dataset.reducedMotion === "true";\n'
    'document.getElementById("step").addEventListener("click", step);\n'
    'document.getElementById("play").addEventListener("click", function () {\n'
    "  if (still) { step(); return; }\n"
    "  if (timer) { clearInterval(timer); timer = null; return; }\n"
    "  timer = setInterval(step, 1000);\n"
    "});\n"
)
BUTTONS = (
    '<div class="row">\n'
    '<button type="button" id="play" aria-label="Play the reaction">Play</button>\n'
    '<button type="button" id="step" aria-label="Show the next stage">Step</button>\n'
    "</div>\n"
)
IRON_AT_THE_BAR = (
    f"<style>\n{DESIGN}{CHIPS}.kv .eq{{font-size:16px;font-weight:600}}\n</style>\n"
    '<div class="kv">\n'
    '<p class="eq">Fe + 2 CH3COOH &#8594; Fe(CH3COO)2 + H2</p>\n'
    '<div class="row" id="cast"></div>\n'
    '<p id="said" aria-live="polite"></p>\n'
    f"{BUTTONS}"
    "</div>\n"
    "<script>\n"
    'const data = JSON.parse(document.getElementById("kv-data").textContent);\n'
    "const stages = [\n"
    '  ["Iron", "Fe"],\n'
    '  ["Acetic acid", "CH3COOH"],\n'
    '  ["Iron(II) acetate", "Fe(CH3COO)2"],\n'
    '  ["Hydrogen", "H2"]\n'
    "];\n"
    'const cast = document.getElementById("cast");\n'
    "const chips = stages.map(function (stage) {\n"
    '  const chip = document.createElement("span");\n'
    '  chip.setAttribute("class", "chip");\n'
    '  chip.textContent = stage[0] + " (" + stage[1] + ")";\n'
    "  cast.appendChild(chip);\n"
    "  return chip;\n"
    "});\n"
    "function step() {\n"
    "  shown = shown % stages.length + 1;\n"
    '  chips.forEach(function (chip, index) { chip.setAttribute("class", index === shown - 1 ? "chip on" : "chip"); });\n'
    '  document.getElementById("said").textContent = stages[shown - 1][0] + " joins the reaction.";\n'
    "}\n"
    f"{STEPPER}"
    "</script>"
)
KUT_AT_THE_BAR = (
    f"<style>\n{DESIGN}{CHIPS}</style>\n"
    '<div class="kv">\n'
    "<p>Iron in kut paste meets the tannic acid of harde on the cloth.</p>\n"
    '<div class="row" id="cast"></div>\n'
    '<p id="said" aria-live="polite"></p>\n'
    f"{BUTTONS}"
    "</div>\n"
    "<script>\n"
    'const data = JSON.parse(document.getElementById("kv-data").textContent);\n'
    'const stages = ["Iron in kut paste", "Tannic acid from harde", "Deep fast chocolate-black colour"];\n'
    'const cast = document.getElementById("cast");\n'
    "const chips = stages.map(function (stage) {\n"
    '  const chip = document.createElement("span");\n'
    '  chip.setAttribute("class", "chip");\n'
    "  chip.textContent = stage;\n"
    "  cast.appendChild(chip);\n"
    "  return chip;\n"
    "});\n"
    "function step() {\n"
    "  shown = shown % stages.length + 1;\n"
    '  chips.forEach(function (chip, index) { chip.setAttribute("class", index === shown - 1 ? "chip on" : "chip"); });\n'
    '  document.getElementById("said").textContent = shown === stages.length\n'
    '    ? "The iron oxidises with the tannic acid and the print turns black."\n'
    '    : stages[shown - 1] + " joins the reaction.";\n'
    "}\n"
    f"{STEPPER}"
    "</script>"
)


def at_the_bar(html: str) -> dict[str, str]:
    return {"html": html, "htmlSha256": hashlib.sha256(html.encode("utf-8")).hexdigest()}
