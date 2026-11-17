import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

import { BLOCK_KINDS, BUILT_BLOCK_KINDS, DEPTHS, DISCIPLINES, FINAL_SECTION_STATES, IMAGE_RELEVANCE, MEDIA_DISPLAYS, TERM_BASES, WORKING_SECTION_STATES } from "@/lib/explainerContract";
import { TRAIL_GROUPS, TRAIL_STAGES } from "@/lib/explainerStream";
import { MEDIA_JOB_STATUSES, MEDIA_KINDS } from "@/lib/mediaContract";
import { AGGREGATIONS, ENV_STATS, PLACE_BASES, PLACE_SCOPES, REGION_FACETS } from "@/lib/regionContract";
import { CONDITION_QUANTITIES, ENVELOPE_STATUSES, MATERIAL_KINDS, MATERIAL_ROLES, REACTION_KINDS, STAGE_TYPES } from "@/lib/scienceContract";
import { CLIENT_TOOL_NAMES, RELAY_AUDIO_TYPES, VOICE_MODES } from "@/lib/voiceContract";

const BACKEND = join(__dirname, "..", "..", "backend", "app");
const sources = new Map<string, string>();

function backendTuple(file: string, name: string): string[] {
  const text = sources.get(file) ?? readFileSync(join(BACKEND, ...file.split("/")), "utf8");
  sources.set(file, text);
  const found = new RegExp(`^${name} = \\(([^)]*)\\)`, "m").exec(text);
  if (!found) throw new Error(`${name} is not a tuple in backend/app/${file}`);
  return [...found[1].matchAll(/"([^"]+)"/g)].map((value) => value[1]);
}

const PAIRS: [string, string, readonly string[]][] = [
  ["models/enums.py", "STAGE_TYPES", STAGE_TYPES],
  ["models/enums.py", "MATERIAL_KINDS", MATERIAL_KINDS],
  ["models/enums.py", "MATERIAL_ROLES", MATERIAL_ROLES],
  ["models/enums.py", "REACTION_KINDS", REACTION_KINDS],
  ["models/enums.py", "ENV_STATS", ENV_STATS],
  ["models/enums.py", "MEDIA_KINDS", MEDIA_KINDS],
  ["schemas/science.py", "CONDITION_QUANTITIES", CONDITION_QUANTITIES],
  ["schemas/science.py", "ENVELOPE_STATUSES", ENVELOPE_STATUSES],
  ["schemas/region.py", "REGION_FACETS", REGION_FACETS],
  ["schemas/region.py", "AGGREGATIONS", AGGREGATIONS],
  ["schemas/region.py", "PLACE_SCOPES", PLACE_SCOPES],
  ["schemas/region.py", "PLACE_BASES", PLACE_BASES],
  ["schemas/voice.py", "VOICE_MODES", VOICE_MODES],
  ["schemas/voice.py", "RELAY_AUDIO_TYPES", RELAY_AUDIO_TYPES],
  ["schemas/voice.py", "CLIENT_TOOL_NAMES", CLIENT_TOOL_NAMES],
  ["schemas/media.py", "MEDIA_JOB_STATUSES", MEDIA_JOB_STATUSES],
  ["models/enums.py", "EXPLAINER_DEPTHS", DEPTHS],
  ["models/enums.py", "DISCIPLINES", DISCIPLINES],
  ["models/enums.py", "BLOCK_KINDS", BLOCK_KINDS],
  ["research/explainer.py", "BUILT_BLOCK_KINDS", BUILT_BLOCK_KINDS],
  ["research/explainer.py", "WORKING_SECTION_STATES", WORKING_SECTION_STATES],
  ["research/explainer.py", "FINAL_SECTION_STATES", FINAL_SECTION_STATES],
  ["research/explainer.py", "TRAIL_STAGES", TRAIL_STAGES],
  ["research/explainer.py", "TRAIL_GROUPS", TRAIL_GROUPS],
  ["models/enums.py", "MEDIA_DISPLAYS", MEDIA_DISPLAYS],
  ["models/enums.py", "IMAGE_RELEVANCE", IMAGE_RELEVANCE],
  ["models/enums.py", "TERM_BASES", TERM_BASES]
];

for (const [file, name, client] of PAIRS) {
  test(`${name} matches backend/app/${file} value for value, in order`, () => {
    expect([...client]).toEqual(backendTuple(file, name));
  });
}

test("a name the backend file does not define fails instead of matching nothing", () => {
  expect(() => backendTuple("models/enums.py", "NOT_A_TUPLE")).toThrow("NOT_A_TUPLE is not a tuple");
});
