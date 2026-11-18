from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from types import MappingProxyType

from app.composer.region_story import (
    NO_CHOICE,
    REPLY_LAYERS_MAX,
    REPLY_STEPS_MAX,
    StoryChoice,
    StoryStepChoice,
)
from app.geo.layers import LAYERS_BY_ID
from app.research.blocks import ExplainerSentence, stated_texts
from app.research.blocks_climate import ClimateRiskBlock
from app.research.blocks_place import RegionStoryBlock, SeasonRow, SeasonsBlock
from app.research.calendar import MONTH_NAMES, first_season, months_named
from app.research.craft_page import EnvironmentStep, OverviewSection, PageClaim, PagePlace
from app.research.craft_parts import (
    AreaName,
    ChapterPlace,
    EntryPlace,
    PlacesPart,
    PlatePart,
    RecordEntry,
    RecordPart,
)
from app.research.vocabulary import FACT_LEVELS
from app.science.records import KnownClaim

from .chapter_context import ChapterContext
from .chapter_draft import ChapterDraft, Drafted
from .chapter_plates import PicturePlan, placed_records
from .chapter_prose import prose_blocks
from .climate_risk import MEANING_WORDS, climate_risk_block
from .region_story import DISTRICT_REF_PREFIX, region_story_block

__all__ = [
    "FACTOR_LAYERS",
    "FACTOR_WORDS",
    "MEANING_MAX",
    "SEASON_DISCIPLINES",
    "STORY_ROLES",
    "story_choice",
    "why_chapter",
]

KEY = "why"
STORY_ROLES = (
    "PRACTISED",
    "ORIGIN",
    "HISTORIC_CENTRE",
    "MIGRATED_FROM",
    "MIGRATED_TO",
    "MATERIAL_SOURCE",
    "MARKET",
)
FACTOR_WORDS: Mapping[str, str] = MappingProxyType(
    {
        "WATER": "Water",
        "SOIL": "Soil",
        "CLIMATE": "Climate",
        "LANDFORM": "Landform",
        "VEGETATION": "Vegetation",
        "OTHER": "Setting",
    }
)
FACTOR_LAYERS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "WATER": ("annual-precipitation", "monsoon-share", "river-density", "distance-to-major-river"),
        "SOIL": (
            "soil-ph-0-5cm",
            "soil-organic-carbon-0-5cm",
            "clay-0-5cm",
            "sand-0-5cm",
            "cation-exchange-0-5cm",
        ),
        "CLIMATE": (
            "annual-mean-temperature",
            "warmest-month-maximum",
            "coldest-month-minimum",
            "annual-precipitation",
        ),
        "LANDFORM": ("elevation", "slope", "mineral-sites"),
        "VEGETATION": (
            "tree-cover-2000",
            "forest-loss-2001-2025",
            "tree-cover-share",
            "cropland-share",
            "bare-ground-share",
        ),
    }
)
MEANING_MAX = 6
SEASON = "SEASON"
SEASON_DISCIPLINES = frozenset({"PROCESS", "CLIMATE", "MATERIALS", "BOTANY", "ECOLOGY", "GEOGRAPHY"})
SUBJECT_LABELLED = frozenset({"STAGE", "MATERIAL", "TOOL"})
SEASON_LABEL_MAX = 120


def why_chapter(
    ctx: ChapterContext,
    sections: Sequence[OverviewSection],
    plan: PicturePlan,
    found: tuple[Sequence[EnvironmentStep], Sequence[PagePlace]],
) -> ChapterDraft:
    environment, places = found
    items = [Drafted.of_block(block) for block in prose_blocks(ctx, KEY, sections)]
    record, loose = placed_records(plan, KEY, _environment(ctx, environment, plan))
    if record is not None:
        items.append(Drafted.of_part(record))
    items += [Drafted.of_part(plate) for plate in loose]
    story = _region_story(ctx, places, environment)
    if story is not None:
        names = ", ".join(district.name for district in story.districts[:3])
        items.append(Drafted.of_block(story, figure={"craft": ctx.craft_name, "places": names}))
    climate = _climate(ctx, environment, places)
    if climate is not None:
        items.append(Drafted.of_block(climate, figure={"finding": _finding(climate)}))
    seasons = _seasons(ctx)
    if seasons is not None:
        items.append(Drafted.of_block(seasons, figure={"craft": ctx.craft_name}))
    shown = _places(ctx, places)
    if shown is not None:
        items.append(Drafted.of_part(shown))
    items += [Drafted.of_part(PlatePart(kind="plate", plate=p.plate)) for p in plan.plates(KEY)]
    return ChapterDraft(KEY, plan.opener(KEY), items)


def _environment(
    ctx: ChapterContext, steps: Sequence[EnvironmentStep], plan: PicturePlan
) -> RecordPart | None:
    entries = []
    for n, step in enumerate(steps, start=1):
        sentences = ctx.facts(step.claim_ids, f"why.env{n}")
        if sentences:
            place = EntryPlace(key=step.place.key, name=step.place.name) if step.place else None
            label = FACTOR_WORDS[step.factor]
            entries.append(
                RecordEntry(
                    label=label,
                    start=None,
                    end=None,
                    factor=step.factor,
                    place=place,
                    sentences=sentences,
                    plate=None,
                )
            )
    return RecordPart(kind="record", entries=entries) if entries else None


def _region_story(
    ctx: ChapterContext, places: Sequence[PagePlace], environment: Sequence[EnvironmentStep]
) -> RegionStoryBlock | None:
    offer = ctx.rows.region
    if offer is None:
        return None
    statements: dict[str, KnownClaim] = {}
    steps = []
    ranked = sorted(
        places,
        key=lambda place: STORY_ROLES.index(place.role) if place.role in STORY_ROLES else len(STORY_ROLES),
    )
    for place in ranked:
        lgd = place.district.lgd if place.district else None
        if lgd is None or lgd not in offer.districts:
            continue
        claim = next(
            (
                fact
                for claim_id in place.claim_ids
                if (fact := ctx.known(claim_id)) and fact.level in FACT_LEVELS
            ),
            None,
        )
        if claim is None or any(known.id == claim.id for known in statements.values()):
            continue
        ref = f"c{len(statements) + 1}"
        statements[ref] = claim
        steps.append(StoryStepChoice(claim=ref, district=f"{DISTRICT_REF_PREFIX}{lgd}"))
    if not steps:
        return None
    factors = {step.factor for step in environment}
    wanted = {layer for factor in factors for layer in FACTOR_LAYERS.get(factor, ())}
    layers = [layer.id for layer in offer.layers if layer.id in wanted and layer.id in LAYERS_BY_ID]
    return region_story_block(offer, statements, story_choice(steps, layers), block_id="why.region")


def story_choice(steps: Sequence[StoryStepChoice], layers: Sequence[str]) -> StoryChoice:
    return StoryChoice(
        river=NO_CHOICE, steps=list(steps[:REPLY_STEPS_MAX]), layers=list(layers[:REPLY_LAYERS_MAX])
    )


def _climate(
    ctx: ChapterContext, environment: Sequence[EnvironmentStep], places: Sequence[PagePlace]
) -> ClimateRiskBlock | None:
    climate = ctx.rows.climate
    if not climate.trends:
        return None
    claim_ids = [
        *(c for step in environment for c in step.claim_ids),
        *(c for place in places for c in place.claim_ids),
    ]
    meaning: dict[str, KnownClaim] = {}
    for claim_id in dict.fromkeys(claim_ids):
        fact = ctx.known(claim_id)
        if fact is not None and fact.level in FACT_LEVELS and MEANING_WORDS.search(fact.text):
            meaning[f"c{len(meaning) + 1}"] = fact
        if len(meaning) == MEANING_MAX:
            break
    block = climate_risk_block(climate, meaning, list(meaning), block_id="why.climate")
    shown = {(trend.district.district_lgd, trend.variable) for trend in block.trends}
    series = [item for item in ctx.rows.series if (item.district.district_lgd, item.variable) in shown]
    if not series:
        return block
    return ClimateRiskBlock.model_validate({**block.model_dump(by_alias=True), "series": series})


def _finding(block: ClimateRiskBlock) -> str:
    trend = block.trends[0]
    word = "rainfall" if "precipitation" in trend.variable else "temperature"
    if not trend.significant:
        return f"Annual {word} in {trend.district.name}, {trend.period}: no significant trend"
    direction = "rising" if trend.slope_per_decade > 0 else "falling"
    return f"Annual {word} in {trend.district.name}, {trend.period}: {direction} {abs(trend.slope_per_decade):.3g} {trend.slope_unit}"


def _seasons(ctx: ChapterContext) -> SeasonsBlock | None:
    rows: list[SeasonRow] = []
    curated = ctx.records.curated
    for entry in curated.stages if curated else []:
        if entry.season is None or entry.season.claim_id not in ctx.claims:
            continue
        sentence = ctx.sentence(entry.season.claim_id, f"why.season{len(rows) + 1}")
        if sentence is not None and sentence.level in FACT_LEVELS:
            row = _season_row(entry.stage_id, _stage_name(ctx, entry.stage_id), sentence)
            rows += [row] if row is not None else []
    staged = {citation.claim_id for row in rows for citation in row.sentence.citations}
    for claim_id in ctx.dossier_ordered(ctx.own):
        claim = ctx.claims[claim_id]
        if str(claim.id) in staged or claim.level not in FACT_LEVELS:
            continue
        sentence = ctx.sentence(claim.id, f"why.season{len(rows) + 1}")
        label = _claim_label(claim, sentence) if claim.discipline in SEASON_DISCIPLINES else None
        row = _season_row(None, label, sentence) if sentence is not None and label is not None else None
        rows += [row] if row is not None else []
    if not rows:
        return None
    rain = ctx.rows.rainfall
    datasets = [rain.dataset] if rain is not None else []
    return SeasonsBlock(
        id="why.seasons",
        kind="seasons",
        version=1,
        reuse=None,
        rows=rows,
        rainfall=rain.rain if rain else None,
        datasets=datasets,
    )


def _season_row(stage_id: uuid.UUID | None, label: str, sentence: ExplainerSentence) -> SeasonRow | None:
    texts = stated_texts(sentence)
    months = sorted(months_named(texts))
    season = first_season(texts)
    if stage_id is None and not months and season is None:
        return None
    return SeasonRow(stage_id=stage_id, label=label, months=months, season=season, sentence=sentence)


def _claim_label(claim: PageClaim, sentence: ExplainerSentence) -> str | None:
    if claim.subject.kind in SUBJECT_LABELLED and len(claim.subject.name) <= SEASON_LABEL_MAX:
        return claim.subject.name
    texts = stated_texts(sentence)
    season = first_season(texts)
    if season is not None:
        return season.capitalize()
    months = sorted(months_named(texts))
    if not months:
        return None
    names = [MONTH_NAMES[month - 1] for month in months]
    if len(months) > 1 and months == list(range(months[0], months[-1] + 1)):
        return f"{names[0]} to {names[-1]}"
    return ", ".join(names)


def _stage_name(ctx: ChapterContext, stage_id: uuid.UUID) -> str:
    return next((stage.name for stage in ctx.records.process.stages if stage.id == stage_id), "Stage")


def _places(ctx: ChapterContext, places: Sequence[PagePlace]) -> PlacesPart | None:
    grouped: dict[str, list[PagePlace]] = {}
    for place in places:
        grouped.setdefault(place.name.casefold(), []).append(place)
    shown = []
    for group in grouped.values():
        first = group[0]
        sentences = ctx.facts(
            [c for place in group for c in place.claim_ids], f"why.place-{first.key.lower()}"
        )
        if not sentences:
            continue
        shown.append(
            ChapterPlace(
                key=first.key,
                name=first.name,
                kind=first.kind,
                roles=list(dict.fromkeys(place.role for place in group)),
                district=AreaName(lgd=first.district.lgd, name=first.district.name)
                if first.district
                else None,
                state=AreaName(lgd=first.state.lgd, name=first.state.name) if first.state else None,
                country=first.country,
                wikidata_id=first.wikidata_id,
                sentences=sentences,
            )
        )
    return PlacesPart(kind="places", places=shown) if shown else None
