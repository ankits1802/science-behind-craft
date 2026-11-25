from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import Any

from app.research.component_specs_science_lab import ChoiceToggleSpec, ExperimentLabSpec, ResultText
from app.research.component_specs_science_parts import Styled

from .page_export_figures import FigureAsk, prefixed, scene_of
from .page_export_model import ExportFigure, ExportText, Run, plain_text
from .page_export_science import raw_at
from .page_export_units import rich_runs
from .page_export_words import DRAWN_IN

__all__ = ["choice_toggle_figure", "experiment_lab_figure"]

PARTS = "parts"
PART = "part"


def experiment_lab_figure(ask: FigureAsk, spec: object) -> ExportFigure | None:
    if not isinstance(spec, ExperimentLabSpec):
        return None
    titles = {component.label: component.title for component in ask.texts.content.components}
    lines: list[ExportText | None] = [plain_text(spec.picker_label, "note")]
    for number, experiment in enumerate(spec.experiments, start=1):
        shown = titles.get(experiment.toggle.component)
        where = f" ({ask.words.said(DRAWN_IN, title=shown)})" if shown else ""
        lines.append(plain_text(f"{number}. {experiment.label}{where}", "item"))
    ask.replaced(spec.number)
    return ask.figure([], lines, ask.entry.title)


def choice_toggle_figure(ask: FigureAsk, spec: object) -> ExportFigure | None:
    if not isinstance(spec, ChoiceToggleSpec):
        return None
    lines: list[ExportText | None] = []
    for option in spec.options:
        lines.append(prefixed(f"{option.label}: ", ask.unit(option.heading)))
        for part in option.parts:
            if isinstance(part, ResultText):
                lines.append(ask.unit(part.unit))
            else:
                lines += [plain_text(part.differs.summary, "note"), *ask.units(part.differs.body)]
    raw = [*(raw_at(ask, "textParts") or []), *(raw_at(ask, "visualParts") or [])]
    lines += list(_panel_lines(ask, raw))
    stills = [scene_of(part.get("drawing")) for part in _flat(raw) if part.get(PART) == "stage"]
    return ask.figure(stills, lines, ask.title(spec.question))


def _panel_lines(ask: FigureAsk, parts: Sequence[Any]) -> Iterator[ExportText | None]:
    for part in _flat(parts):
        kind = part.get(PART)
        if kind == "text":
            yield ask.unit((part.get("text") or {}).get("unit"))
        elif kind == "formulas":
            yield from (_chip(chip) for chip in part.get("chips", []))
        elif kind == "same":
            yield ask.unit(part.get("label"), "subheading")
            yield from ask.units(part.get("paragraphs", []))
        elif kind in ("chart", "stage"):
            yield ask.unit(part.get("title") or part.get("note"), "note")
            yield ask.unit(part.get("source"), "credit")


def _chip(chip: dict[str, Any]) -> ExportText:
    formula = rich_runs(
        [item if isinstance(item, str) else Styled.model_validate(item) for item in chip.get("formula", [])]
    )
    record = f"PubChem CID {chip['cid']}" if chip.get("cid") else str(chip.get("source") or "")
    runs = (*formula, Run(f" · {chip.get('name', '')}"), *((Run(f" · {record}"),) if record else ()))
    return ExportText(runs=runs, role="body")


def _flat(parts: Sequence[Any]) -> Iterator[dict[str, Any]]:
    for part in parts:
        if not isinstance(part, dict):
            continue
        if part.get(PART) == "more":
            yield from _flat(part.get(PARTS, []))
        else:
            yield part
