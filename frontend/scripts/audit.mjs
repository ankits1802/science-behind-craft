import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";

const EXCEPTIONS_FILE = new URL("../audit-exceptions.json", import.meta.url);

function runAudit(extraArgs) {
  const args = ["audit", "--json", ...extraArgs];
  const options = { encoding: "utf8", maxBuffer: 64 * 1024 * 1024, shell: process.platform === "win32" };
  try {
    return JSON.parse(execFileSync("npm", args, options));
  } catch (error) {
    if (typeof error.stdout === "string" && error.stdout.trim().startsWith("{")) {
      return JSON.parse(error.stdout);
    }
    throw error;
  }
}

function advisories(report) {
  const found = new Map();
  for (const [name, entry] of Object.entries(report.vulnerabilities ?? {})) {
    for (const via of entry.via ?? []) {
      if (typeof via !== "object" || typeof via.url !== "string") continue;
      const id = via.url.split("/").pop();
      const known = found.get(id) ?? { id, severity: via.severity, packages: new Set() };
      known.packages.add(name);
      found.set(id, known);
    }
  }
  return found;
}

function describe(advisory) {
  return `${advisory.id} (${advisory.severity}) in ${[...advisory.packages].sort().join(", ")}`;
}

const exceptions = JSON.parse(readFileSync(EXCEPTIONS_FILE, "utf8"));
const excepted = new Set(exceptions.map((entry) => entry.advisory));
const problems = [];

for (const advisory of advisories(runAudit(["--omit=dev"])).values()) {
  problems.push(`production dependency advisory ${describe(advisory)}: no exception applies to production dependencies`);
}

const everything = advisories(runAudit([]));
for (const advisory of everything.values()) {
  if (!excepted.has(advisory.id)) {
    problems.push(`advisory ${describe(advisory)} has no entry in audit-exceptions.json`);
  }
}
for (const entry of exceptions) {
  if (!everything.has(entry.advisory)) {
    problems.push(`audit-exceptions.json lists ${entry.advisory}, which the audit no longer reports: remove it`);
  }
}

for (const problem of problems) console.error(problem);
if (problems.length > 0) process.exit(1);
console.log(`audit passed: production dependencies clean; ${everything.size} excepted development advisories`);
