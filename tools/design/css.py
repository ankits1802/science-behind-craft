from __future__ import annotations

from typing import Any

from design.system import System

__all__ = ["css", "theme_css"]

INDENT = "\n  "
GRAIN_TILE = (
    "--grain: url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E"
    "%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/%3E"
    "%3CfeColorMatrix values='0 0 0 0 {red:.2f} 0 0 0 0 {green:.2f} 0 0 0 0 {blue:.2f} 0 0 0 {alpha:.3f} 0'/%3E"
    "%3C/filter%3E%3Crect width='160' height='160' filter='url(%23n)'/%3E%3C/svg%3E\");"
)
SCOPES = (("light", "light"), ("dark", "dark"), ("hcl", "hcLight"), ("hcd", "hcDark"))
NO_OS_STANDARD = ':not([data-high-contrast="false"])'


def _colour_lines(tokens: dict[str, Any], theme: str) -> list[str]:
    lines = [f"--c-{name}: {entry[theme]['channels']};" for name, entry in tokens["color"].items()]
    for key, entry in tokens["plate"].items():
        if key != "rules":
            lines.append(
                f"--plate-{key}: {entry[theme]['ground']}; --plate-{key}-ink: {entry[theme]['ink']};"
            )
    return lines


def _data_lines(tokens: dict[str, Any], theme: str) -> list[str]:
    dataviz = tokens["dataviz"]
    lines = [
        " ".join(f"--{key}-{i + 1}: {step};" for i, step in enumerate(ramp[theme]["steps"]))
        for key, ramp in dataviz["ramps"].items()
    ]
    families = dataviz["categorical"]
    named = " ".join(f"--fam-{name}: {colour};" for name, colour in families[theme]["colors"].items())
    lines.append(f"{named} --fam-other: {families['other'][theme]};")
    lines += [f"--{name}: {entry[theme]['hex']};" for name, entry in dataviz["chart"].items()]
    lines += [
        f"--{name}: {entry[theme]['hex']};"
        for name, entry in dataviz["map"].items()
        if name not in ("rules", "map-hillshade")
    ]
    return lines


def _grain_line(grain: str) -> str:
    if grain == "none":
        return "--grain: none;"
    red, green, blue, alpha = grain[5:-1].split(",")
    return GRAIN_TILE.format(
        red=int(red) / 255, green=int(green) / 255, blue=int(blue) / 255, alpha=float(alpha)
    )


def theme_css(tokens: dict[str, Any], system: System, theme: str) -> str:
    shadow = tokens["shadow"]
    effects = [
        f"--shadow-pop: {shadow['pop'][theme]}; --shadow-label: {shadow['label'][theme]}; --shadow-sheet: {shadow['sheet'][theme]};",
        _grain_line(tokens["grain"][theme]),
        f"--map-hillshade-opacity: {system.data['hillshadeOpacity'][theme]};",
    ]
    return INDENT.join([*_colour_lines(tokens, theme), *_data_lines(tokens, theme), *effects])


def _script_lines(tokens: dict[str, Any], system: System) -> list[str]:
    fallbacks = system.data["scriptFallbacks"]
    lines = []
    for code, script in tokens["type"]["scripts"].items():
        if code == "rules":
            continue
        names = script["cssVars"]
        reading = f'"{script["reading"]}", "{script["ui"]}", {fallbacks[script["direction"]]}'
        lines.append(f'{names["reading"]}: {reading}; {names["ui"]}: "{script["ui"]}", {fallbacks["ui"]};')
    return lines


def _scale_lines(tokens: dict[str, Any]) -> list[str]:
    lines = [
        f"--text-{name}: {s['value']}; --lh-{name}: {s['lineHeight']}; --track-{name}: {s['tracking']};"
        for name, s in tokens["type"]["scale"].items()
    ]
    lines += [
        f"--{key}: {value['rem']};" if "rem" in value else f"--space-{key}: {value['value']};"
        for key, value in tokens["space"].items()
    ]
    lines.append(" ".join(f"--{key}: {value['rem']};" for key, value in tokens["control"].items()))
    lines += [f"--radius-{key}: {value['px']}px;" for key, value in tokens["radius"].items()]
    lines += [f"--dur-{key}: {value};" for key, value in tokens["motion"]["durations"].items()]
    return lines


def _static_css(tokens: dict[str, Any], system: System) -> str:
    families = tokens["type"]["families"]
    lines = [
        "--text-zoom: 1;",
        *(f"--font-{name}: {families[name]['stack']};" for name in ("headline", "reading", "ui", "code")),
    ]
    lines += _script_lines(tokens, system) + _scale_lines(tokens)
    lines.append(system.data["staticCss"][0])
    lines += [f"--z-{key}: {value};" for key, value in tokens["z"].items()]
    lines += system.data["staticCss"][1:]
    lines += [
        f"{entry['cssVar']}: {entry['hex']};" for entry in tokens["specimen"].values() if "hex" in entry
    ]
    lines += [
        f"--{name}: {tokens['specimen'][name]['value']};"
        for name in ("photo-scrim-start", "photo-scrim-bottom")
    ]
    lines += [f"--{name}: {value};" for name, value in system.data["staticColours"].items()]
    lines.append(_hex_aliases(tokens))
    return INDENT.join(lines)


def _hex_aliases(tokens: dict[str, Any]) -> str:
    return " ".join(f"--{name}: rgb(var(--c-{name}));" for name in tokens["color"])


def _rule(selector: str, body: str) -> str:
    return f"{selector} {{{INDENT}{body}\n}}"


def _media(query: str, selector: str, body: str) -> str:
    return f"@media {query} {{\n  {selector} {{{INDENT}{body}\n  }}\n}}"


def _theme_blocks(tokens: dict[str, Any], system: System) -> list[str]:
    dark = "color-scheme: dark;" + INDENT + theme_css(tokens, system, "dark")
    high_light = theme_css(tokens, system, "hcLight")
    high_dark = theme_css(tokens, system, "hcDark")
    return [
        _rule(
            ":root",
            "color-scheme: light;"
            + INDENT
            + _static_css(tokens, system)
            + INDENT
            + theme_css(tokens, system, "light"),
        ),
        _media("(prefers-color-scheme: dark)", ':root:not([data-theme="light"])', dark),
        _rule(':root[data-theme="dark"]', dark),
        _media("(prefers-contrast: more)", f":root{NO_OS_STANDARD}", high_light),
        _media(
            "(prefers-contrast: more) and (prefers-color-scheme: dark)",
            f':root{NO_OS_STANDARD}:not([data-theme="light"])',
            high_dark,
        ),
        _media("(prefers-contrast: more)", f':root[data-theme="dark"]{NO_OS_STANDARD}', high_dark),
        _rule(':root[data-high-contrast="true"]', high_light),
        _media(
            "(prefers-color-scheme: dark)",
            ':root[data-high-contrast="true"]:not([data-theme="light"])',
            high_dark,
        ),
        _rule(':root[data-theme="dark"][data-high-contrast="true"]', high_dark),
    ]


def _scope_blocks(tokens: dict[str, Any], system: System) -> str:
    blocks = []
    for key, theme in SCOPES:
        scheme = "dark" if "ark" in theme else "light"
        body = INDENT.join(
            [
                f"color-scheme: {scheme};",
                theme_css(tokens, system, theme),
                _hex_aliases(tokens),
                "color: var(--ink-1);",
            ]
        )
        blocks.append(_rule(f".tscope-{key}", body))
    return "\n".join(blocks)


def _script_selectors(tokens: dict[str, Any]) -> str:
    rows = []
    for code, script in tokens["type"]["scripts"].items():
        if code == "rules":
            continue
        names = script["cssVars"]
        rows.append(
            f'[data-script="{code}"] {{ font-family: var({names["reading"]}); --script-scale: {script["scale"]}; '
            f"--script-leading: {script['leading']}; --script-display-leading: {script['displayLeading']}; }}"
        )
        rows.append(
            f'[data-script="{code}"].ui, .ui [data-script="{code}"] {{ font-family: var({names["ui"]}); }}'
        )
    return "\n".join(rows)


def css(tokens: dict[str, Any], system: System) -> str:
    larger = ':root[data-larger-text="true"] { font-size: 112.5%; --text-zoom: 1.125; }'
    blocks = [
        *_theme_blocks(tokens, system),
        larger,
        _script_selectors(tokens),
        _scope_blocks(tokens, system),
    ]
    return "\n".join(blocks) + "\n"
