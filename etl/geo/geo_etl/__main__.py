import argparse
import dataclasses
import datetime as dt
import json
import re
import sys
import time
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from geo_etl import catalog
from geo_etl.districts import SHAPES_PATH, districts_without_shapes, load_districts, sha256_of
from geo_etl.layers import Options, Result, chelsa, chirps, copdem, geology, hansen, hydrorivers, soilgrids, worldcover
from geo_etl.layers.geology import GEOLOGY_COLUMNS
from geo_etl.rows import COLUMNS

ROOT = Path(__file__).resolve().parent.parent
LAYERS: dict[str, Callable[..., Result]] = {
    "soilgrids": soilgrids.run,
    "worldcover": worldcover.run,
    "hansen": hansen.run,
    "chelsa": chelsa.run,
    "chirps": chirps.run,
    "copdem": copdem.run,
    "hydrorivers": hydrorivers.run,
    "mrds": geology.run_mrds,
    "glim": geology.run_glim,
}
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
DATASET_LABELS = {
    "SOILGRIDS_2_0": "SoilGrids-2-0",
    "ESA_WORLDCOVER_2021_V200": "ESA-WorldCover-2021-v200",
    "HANSEN_GFC_2025_V1_13": "Hansen-GFC-2025-v1-13",
    "CHELSA_2_1_1981_2010": "CHELSA-2-1-1981-2010",
    "CHIRPS_3_0": "CHIRPS-3-0",
    "COPERNICUS_DEM_GLO90": "Copernicus-DEM-GLO-90",
    "HYDRORIVERS_1_0": "HydroRIVERS-1-0",
    "USGS_MRDS": "USGS-MRDS",
    "GLIM_1_0_05DEG": "GLiM-1-0",
}
CSV_GLOB = "KalaVigyan_Dataset_*_District-Stats.csv"


def dataset_label(code: str) -> str:
    if code in DATASET_LABELS:
        return DATASET_LABELS[code]
    words = [w for w in re.split(r"[^A-Za-z0-9]+", code) if w]
    return "-".join(w if any(c.isdigit() for c in w) else w.capitalize() for w in words)


def district_stats_filename(code: str, generated: dt.datetime) -> str:
    label = dataset_label(code)
    date = generated.astimezone(IST).strftime("%Y-%m-%d")
    return "_".join(part for part in ("KalaVigyan", "Dataset", date, label, "District-Stats") if part) + ".csv"


def write_dataset_csvs(values: pd.DataFrame, out: Path, generated: dt.datetime) -> list[str]:
    for stale in out.glob(CSV_GLOB):
        stale.unlink()
    names = []
    for code, frame in values.groupby("datasetCode", sort=True):
        name = district_stats_filename(str(code), generated)
        frame.to_csv(out / name, index=False, encoding="utf-8", lineterminator="\n")
        names.append(name)
    return names


def parse_ints(text: str | None) -> set[int] | None:
    if not text or text.strip().lower() == "all":
        return None
    return {int(v) for v in text.replace(" ", "").split(",") if v}


def select_shard(districts: pd.DataFrame, shard: str | None):
    if not shard:
        return districts
    index, count = (int(v) for v in shard.split("/"))
    if not 1 <= index <= count:
        raise SystemExit(f"--shard {shard}: expected k/n with 1 <= k <= n")
    areas = districts.groupby("stateLgd")["areaKm2"].sum().sort_values(ascending=False, kind="stable")
    loads = [0.0] * count
    owner: dict[int, int] = {}
    for state, area in areas.items():
        target = min(range(count), key=lambda i: (loads[i], i))
        owner[int(state)] = target + 1
        loads[target] += float(area)
    return districts[districts["stateLgd"].map(owner) == index].reset_index(drop=True)


def options_from(args: argparse.Namespace) -> Options:
    options = Options(cache=Path(args.cache))
    for name in ("worldcover_factor", "hansen_factor", "dem_factor", "chirps_years"):
        if getattr(args, name, None) is not None:
            options = dataclasses.replace(options, **{name: getattr(args, name)})
    if args.soil_vars:
        options = dataclasses.replace(options, soil_vars=tuple(args.soil_vars.split(",")))
    if args.soil_depths:
        options = dataclasses.replace(options, soil_depths=tuple(args.soil_depths.split(",")))
    if args.chelsa_bio:
        options = dataclasses.replace(options, chelsa_bio=tuple(args.chelsa_bio.split(",")))
    return dataclasses.replace(
        options,
        soil_uncertainty=not args.no_soil_uncertainty,
        chelsa_months=not args.no_chelsa_months,
        chirps_monthly=not args.no_chirps_monthly,
        download_striped=args.download_striped,
    )


def extract(args: argparse.Namespace) -> int:
    parts = Path(args.parts)
    parts.mkdir(parents=True, exist_ok=True)
    districts = select_shard(load_districts(parse_ints(args.districts), parse_ints(args.states)), args.shard)
    if districts.empty:
        print("no districts selected", file=sys.stderr)
        return 2
    options = options_from(args)
    failed = 0
    for key in [k.strip() for k in args.datasets.split(",")] if args.datasets != "all" else list(LAYERS):
        started = time.monotonic()
        result = LAYERS[key](districts, options)
        stem = key if args.shard is None else f"{key}-shard{args.shard.replace('/', 'of')}"
        result.values.to_parquet(parts / f"{stem}.parquet", index=False)
        if result.geology is not None:
            result.geology.to_parquet(parts / f"{stem}.geology.parquet", index=False)
        meta = {
            "layer": key,
            "stem": stem,
            "shard": args.shard,
            "dataset": result.dataset.as_row(),
            "retrievedAt": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
            "districts": int(len(districts)),
            "rows": int(len(result.values)),
            "geologyRows": 0 if result.geology is None else int(len(result.geology)),
            "failures": result.failures,
            "notes": result.notes,
            "options": {k: (str(v) if isinstance(v, Path) else v) for k, v in dataclasses.asdict(options).items()},
            "seconds": round(time.monotonic() - started, 1),
        }
        (parts / f"{stem}.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
        failed += len(result.failures)
        print(f"{key}: {meta['rows']} rows, {len(result.failures)} failures, {meta['seconds']} s")
        for item in result.failures:
            print(f"  failure {item['step']} {item['districtLgds'][:5]}: {item['error']}", file=sys.stderr)
    return 1 if failed and not args.allow_failures else 0


def combine(args: argparse.Namespace) -> int:
    parts = Path(args.parts)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    metas = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(parts.glob("*.json"))]
    frames = [pd.read_parquet(parts / f"{m['stem']}.parquet") for m in metas]
    values = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=COLUMNS)
    values = values.sort_values(["districtLgd", "datasetCode", "variable", "depthOrPeriod", "stat"], kind="stable")
    key = ["districtLgd", "datasetCode", "variable", "depthOrPeriod", "stat"]
    duplicates = int(values.duplicated(key).sum())
    if duplicates:
        print(f"{duplicates} duplicate keys in the combined table", file=sys.stderr)
        return 1
    values.to_parquet(out / "district_env.parquet", index=False)
    generated = dt.datetime.now(dt.UTC)
    csv_names = write_dataset_csvs(values, out, generated)
    geo_frames = [pd.read_parquet(p) for p in sorted(parts.glob("*.geology.parquet"))]
    geology_table = pd.concat(geo_frames, ignore_index=True) if geo_frames else pd.DataFrame(columns=GEOLOGY_COLUMNS)
    geology_table.to_parquet(out / "district_geology.parquet", index=False)
    datasets = {m["dataset"]["code"]: {**m["dataset"], "retrievedAt": m["retrievedAt"]} for m in metas}
    boundaries = catalog.BOUNDARIES.as_row() | {"sha256": sha256_of(SHAPES_PATH)}
    summary = {
        "generatedAt": generated.isoformat(timespec="seconds"),
        "boundaries": boundaries,
        "datasets": list(datasets.values()),
        "layers": [
            {k: m[k] for k in ("layer", "shard", "districts", "rows", "geologyRows", "seconds", "notes", "options")}
            | {"datasetCode": m["dataset"]["code"], "failureCount": len(m["failures"]), "failures": m["failures"]}
            for m in metas
        ],
        "rows": int(len(values)),
        "geologyRows": int(len(geology_table)),
        "districts": int(values["districtLgd"].nunique()) if len(values) else 0,
        "variables": (values.groupby("datasetCode")["variable"].nunique().astype(int).to_dict() if len(values) else {}),
        "districtsWithoutShapes": districts_without_shapes(),
        "csv": csv_names,
    }
    (out / "district_env_summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print(f"combined {len(values)} rows over {summary['districts']} districts into {out}")
    return 0


def add_extract_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--datasets", default="all", help=",".join(LAYERS))
    parser.add_argument("--districts", default="all")
    parser.add_argument("--states", default="all")
    parser.add_argument("--parts", default=str(ROOT / "out" / "parts"))
    parser.add_argument("--cache", default=str(Path.home() / ".cache" / "kalavigyan-geo"))
    parser.add_argument("--worldcover-factor", type=int)
    parser.add_argument("--hansen-factor", type=int)
    parser.add_argument("--dem-factor", type=int)
    parser.add_argument("--chirps-years", type=int)
    parser.add_argument("--soil-vars")
    parser.add_argument("--soil-depths")
    parser.add_argument("--chelsa-bio")
    parser.add_argument("--no-soil-uncertainty", action="store_true")
    parser.add_argument("--no-chelsa-months", action="store_true")
    parser.add_argument("--no-chirps-monthly", action="store_true")
    parser.add_argument("--download-striped", action="store_true")
    parser.add_argument("--allow-failures", action="store_true")
    parser.add_argument("--shard", help="k/n: process the k-th of n state groups, balanced by area")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="geo_etl")
    sub = parser.add_subparsers(dest="command", required=True)
    add_extract_args(sub.add_parser("extract"))
    combine_parser = sub.add_parser("combine")
    combine_parser.add_argument("--parts", default=str(ROOT / "out" / "parts"))
    combine_parser.add_argument("--out", default=str(ROOT / "out"))
    run_parser = sub.add_parser("run")
    add_extract_args(run_parser)
    run_parser.add_argument("--out", default=str(ROOT / "out"))
    args = parser.parse_args(argv)
    if args.command == "extract":
        return extract(args)
    if args.command == "combine":
        return combine(args)
    status = extract(args)
    return combine(args) or status


if __name__ == "__main__":
    raise SystemExit(main())
