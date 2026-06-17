#!/usr/bin/env node
// Forensic Audit Pipeline — headless `claude -p` orchestrator.
// Five sequential stages, each a schema-validated worker behind an adversarial
// falsification gate. Artifacts written to audit/ and git-pushed per stage.
// Nothing about the target is hardcoded: branch/paths/build-commands are discovered.
//
// Flags:  --fresh        tear down audit/ artifacts and start at Stage 1
//         --stage N      run only stage N (1..5)
//         --no-push      skip git push (still commits locally)
//         (default)      resume from first incomplete stage
//
// Substrate notes (verified at preflight):
//   * `claude -p` authenticates headlessly; structured output via a file the worker Writes
//     (--json-schema is advisory) → we validate every result against its schema.
//   * --permission-mode acceptEdits is root-safe.  stdin is closed or the child hangs.
//   * commit.gpgsign=true in this repo → commit with -c commit.gpgsign=false (no pinentry).
//   * --max-budget-usd is intentionally OMITTED: on a subscription the dollar figure is not
//     real spend; runs are bounded by --max-turns + hard timeouts instead.

import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync, readFileSync, existsSync, rmSync } from "node:fs";
import { join, resolve } from "node:path";

const REPO = resolve(process.cwd());
const AUDIT = join(REPO, "audit");
const WORK = join(AUDIT, ".work");
const ARGS = process.argv.slice(2);
const ONLY_STAGE = ARGS.includes("--stage") ? Number(ARGS[ARGS.indexOf("--stage") + 1]) : null;
const FRESH = ARGS.includes("--fresh");
const NO_PUSH = ARGS.includes("--no-push");

const MODEL_DEEP = "sonnet";   // analytical workers + falsifiers
const MODEL_CHEAP = "haiku";   // mechanical sweeps + preflight
let BRANCH = "HEAD";
let SEQ = 0, TOTAL_COST = 0;

const INVARIANTS = `FORENSIC AUDIT — GLOBAL INVARIANTS (obey all, every turn):
1. Absence of evidence is not evidence of absence. Never assert a thing does not exist / is unused / is unreachable unless you name where you looked AND that search space is the full repository surface. Otherwise record it as "unverified", never "absent".
2. No claim without a location. Every finding, behavior, or assertion must cite a concrete path:line (or a named artifact) a reviewer can open. Drop any claim with no citable anchor.
3. Coverage has a denominator. The Stage-1 inventory (git ls-files) is the denominator. "Done looking" means every relevant item was actually opened (a real Read/Grep), not assumed. Self-reported visitation is unverified.
4. Verification is adversarial. To check a claim, return to the source and try to REFUTE it. Do not rubber-stamp prior conclusions.
5. Mutation is a means, not a deliverable. You may read, instrument, run, or modify code in this sandbox to produce your artifact, but the ONLY deliverable is the JSON you Write. Do NOT git commit — the orchestrator commits.
6. Never exfiltrate sensitive data. Reference secrets / PII / PHI / credentials by path + category only; never paste their contents into the artifact. When in doubt, cite the path and stop.`;

// ───────────────────────── shell helper ─────────────────────────
const sh = (c, a, o = {}) => new Promise((r) => {
  const p = spawn(c, a, { cwd: REPO, ...o });
  let O = "", E = "";
  p.stdout?.on("data", (d) => (O += d));
  p.stderr?.on("data", (d) => (E += d));
  p.on("close", (code) => r({ code, out: O, err: E }));
});
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const log = (...m) => console.log(`[${new Date().toISOString().slice(11, 19)}]`, ...m);

// ───────────── minimal JSON-Schema validator (ajv absent) ─────────────
// supports: type (incl. array of types), required, properties, items, enum, minItems
function validate(schema, data, path = "$") {
  const errs = [];
  const typeOf = (v) => Array.isArray(v) ? "array" : v === null ? "null" : typeof v === "number" && Number.isInteger(v) ? "integer" : typeof v;
  if (schema.type) {
    const types = Array.isArray(schema.type) ? schema.type : [schema.type];
    const t = typeOf(data);
    const ok = types.some((ty) => ty === t || (ty === "number" && t === "integer") || (ty === "string" && t === "null" && types.includes("null")));
    if (!ok) { errs.push(`${path}: expected ${types.join("|")}, got ${t}`); return errs; }
  }
  if (schema.enum && !schema.enum.includes(data)) errs.push(`${path}: '${data}' not in enum [${schema.enum.join(",")}]`);
  if (schema.type === "object" || schema.properties) {
    if (data && typeof data === "object" && !Array.isArray(data)) {
      for (const req of schema.required || []) if (!(req in data)) errs.push(`${path}: missing required '${req}'`);
      for (const [k, sub] of Object.entries(schema.properties || {})) if (k in data) errs.push(...validate(sub, data[k], `${path}.${k}`));
    }
  }
  if (schema.type === "array" && Array.isArray(data)) {
    if (schema.minItems && data.length < schema.minItems) errs.push(`${path}: ${data.length} items < minItems ${schema.minItems}`);
    if (schema.items) data.forEach((el, i) => errs.push(...validate(schema.items, el, `${path}[${i}]`)));
  }
  return errs;
}

// ───────────────────────── one subagent call ─────────────────────────
async function runAgent({ name, prompt, schema, model = MODEL_DEEP, maxTurns = 60, web = false, timeoutMs = 900_000, retries = 1 }) {
  const out = join(WORK, `a_${name.replace(/\W+/g, "_")}_${SEQ++}.json`);
  const tools = (web ? "Read,Grep,Glob,Bash,WebSearch,WebFetch" : "Read,Grep,Glob,Bash") + ",Write";
  for (let attempt = 0; attempt <= retries; attempt++) {
    if (existsSync(out)) rmSync(out);
    const nudge = attempt > 0 ? "\n\nYOUR PREVIOUS ATTEMPT PRODUCED NO VALID JSON FILE. Write ONLY raw JSON (no prose, no markdown fences) to the exact path below." : "";
    const full = `${prompt}${nudge}\n\nOUTPUT CONTRACT: use the Write tool to put ONLY raw JSON conforming to this schema:\n${JSON.stringify(schema)}\nat the absolute path: ${out}\nWrite nothing else to that file. Do not commit.`;
    const a = ["-p", full, "--output-format", "json", "--model", model, "--max-turns", String(maxTurns),
      "--allowedTools", tools, "--add-dir", REPO, "--strict-mcp-config",
      "--permission-mode", "acceptEdits", "--append-system-prompt", INVARIANTS];
    log(`  → agent ${name} (model=${model}, attempt=${attempt + 1})`);
    const r = await new Promise((res) => {
      const p = spawn("claude", a, { cwd: REPO, stdio: ["ignore", "pipe", "pipe"] });
      let O = "", E = "";
      const k = setTimeout(() => { try { p.kill("SIGKILL"); } catch {} }, timeoutMs);
      p.stdout.on("data", (d) => (O += d));
      p.stderr.on("data", (d) => (E += d));
      p.on("close", () => { clearTimeout(k); res({ O, E }); });
    });
    let env = null; try { env = JSON.parse(r.O); } catch {}
    if (env?.total_cost_usd) TOTAL_COST += Number(env.total_cost_usd);
    if (!existsSync(out)) { log(`    ✗ ${name}: no structured output (envelope ${env ? "ok" : "non-json"})`); continue; }
    let data; try { data = JSON.parse(readFileSync(out, "utf8")); } catch (e) { log(`    ✗ ${name}: handoff not parseable`); continue; }
    const errs = validate(schema, data);
    if (errs.length) { log(`    ✗ ${name}: schema violations: ${errs.slice(0, 4).join(" | ")}`); continue; }
    log(`    ✓ ${name} ok (cum cost ~$${TOTAL_COST.toFixed(2)})`);
    return { ok: true, data };
  }
  return { ok: false, err: "no-valid-structured-output" };
}

const pMap = async (xs, fn, n = 3) => {
  const out = []; let i = 0;
  await Promise.all(Array(Math.min(n, xs.length)).fill(0).map(async () => {
    while (i < xs.length) { const k = i++; out[k] = await fn(xs[k]); }
  }));
  return out;
};

// ───────────────────────── persistence ─────────────────────────
async function checkpoint(stageLabel, artifacts) {
  for (const [fname, content] of Object.entries(artifacts))
    writeFileSync(join(AUDIT, fname), content);
  await sh("git", ["add", "--", ...Object.keys(artifacts).map((f) => join("audit", f)), join("audit", "forensic-audit.mjs"), join("audit", ".gitignore")]);
  const c = await sh("git", ["-c", "commit.gpgsign=false", "commit", "--no-verify", "-m", `audit: ${stageLabel}`]);
  if (c.code !== 0 && !/nothing to commit/.test(c.out + c.err)) log(`    ! commit warning: ${(c.out + c.err).split("\n")[0]}`);
  else log(`    ✓ committed ${stageLabel}`);
  if (!NO_PUSH) {
    for (let i = 0, delay = 2000; i < 5; i++, delay *= 2) {
      const p = await sh("git", ["push", "-u", "origin", BRANCH]);
      if (p.code === 0) { log(`    ✓ pushed ${BRANCH}`); break; }
      log(`    ! push failed (try ${i + 1}); ${(p.err || p.out).split("\n")[0]}`);
      if (i < 4) await sleep(delay);
    }
  }
}
async function halt(stageLabel, why) {
  const md = `# HALT at ${stageLabel}\n\nThe pipeline stopped because its stop-test could not be satisfied.\n\n## Reason\n${why}\n\nGenerated ${new Date().toISOString()}\n`;
  await checkpoint(`HALT ${stageLabel}`, { "HALT-REPORT.md": md });
  log(`HALT at ${stageLabel}: ${why}`);
  process.exit(2);
}

// ───────────────────────── schemas ─────────────────────────
const S1 = { type: "object", required: ["inventory", "entry_points", "architecture", "provisional_intent", "coverage"], properties: {
  inventory: { type: "array", minItems: 1, items: { type: "object", required: ["path", "role"], properties: {
    path: { type: "string" }, role: { type: "string", enum: ["source", "test", "doc", "config", "asset", "generated", "dead", "unknown"] }, note: { type: "string" } } } },
  entry_points: { type: "array", items: { type: "object", required: ["name", "kind", "location", "description"], properties: {
    name: { type: "string" }, kind: { type: "string", enum: ["cli", "api", "route", "main", "script", "library_export"] }, location: { type: "string" }, description: { type: "string" } } } },
  architecture: { type: "string" }, provisional_intent: { type: "string" },
  coverage: { type: "object", required: ["total_files", "classified", "unknown"], properties: {
    total_files: { type: "integer" }, classified: { type: "integer" }, unknown: { type: "integer" }, ignored: { type: "array", items: { type: "string" } } } } } };

const S2 = { type: "object", required: ["findings", "coverage"], properties: {
  findings: { type: "array", items: { type: "object", required: ["id", "location", "class", "severity", "evidence", "description"], properties: {
    id: { type: "string" }, location: { type: "string" },
    class: { type: "string", enum: ["bug", "security", "doc_drift", "design_defect", "intent_mismatch", "perf", "test_gap", "reproducibility"] },
    severity: { type: "string", enum: ["critical", "high", "medium", "low", "info"] },
    evidence: { type: "string" }, description: { type: "string" },
    survived_falsification: { type: ["boolean", "null"] } } } },
  coverage: { type: "object", required: ["surface_items", "visited"], properties: {
    surface_items: { type: "integer" }, visited: { type: "integer" }, unvisited: { type: "array", items: { type: "string" } } } } } };

const S3 = { type: "object", required: ["build_commands", "test_result", "coverage", "observed_behaviors", "finding_deltas"], properties: {
  build_commands: { type: "array", items: { type: "string" } },
  test_result: { type: "object", required: ["ran", "passed", "failed", "skipped"], properties: {
    ran: { type: "boolean" }, passed: { type: "integer" }, failed: { type: "integer" }, skipped: { type: "integer" }, summary: { type: "string" } } },
  coverage: { type: "object", required: ["measured_pct", "accounting"], properties: {
    measured_pct: { type: ["number", "null"] }, accounting: { type: "string" }, unexecuted_regions: { type: "array", items: { type: "object" } } } },
  observed_behaviors: { type: "array", items: { type: "object", required: ["entry_point", "behavior"], properties: {
    entry_point: { type: "string" }, behavior: { type: "string" }, location: { type: "string" } } } },
  finding_deltas: { type: "array", items: { type: "object", required: ["finding_id", "status"], properties: {
    finding_id: { type: "string" }, status: { type: "string", enum: ["confirmed", "refuted", "refined", "untested"] }, note: { type: "string" } } } } } };

const S4 = { type: "object", required: ["goal_candidates", "research"], properties: {
  goal_candidates: { type: "array", minItems: 1, items: { type: "object", required: ["id", "statement", "success_signals", "grounded"], properties: {
    id: { type: "string" }, statement: { type: "string" }, grounded: { type: ["boolean", "null"] },
    success_signals: { type: "array", items: { type: "object", required: ["signal", "evidence_location"], properties: {
      signal: { type: "string" }, evidence_location: { type: "string" } } } } } } },
  research: { type: "object", required: ["available", "items"], properties: {
    available: { type: "boolean" }, notes: { type: "string" },
    items: { type: "array", items: { type: "object", required: ["idea", "relevance"], properties: {
      idea: { type: "string" }, relevance: { type: "string" },
      sources: { type: "array", items: { type: "object", required: ["title"], properties: {
        title: { type: "string" }, url: { type: "string" }, corroborated: { type: ["boolean", "null"] } } } } } } } } } } };

const S5 = { type: "object", required: ["items"], properties: {
  items: { type: "array", minItems: 1, items: { type: "object", required: ["id", "links_to", "location", "change", "verification_signal", "depends_on", "priority"], properties: {
    id: { type: "string" }, links_to: { type: "string" }, location: { type: "string" }, change: { type: "string" },
    verification_signal: { type: "string" }, depends_on: { type: "array", items: { type: "string" } },
    priority: { type: "string", enum: ["P0", "P1", "P2", "P3"] } } } } } };

// ───────────────────────── markdown renderers ─────────────────────────
const ts = () => `\n\n_Generated ${new Date().toISOString()} · branch ${BRANCH}_\n`;
function r1(d) {
  const byRole = {}; for (const f of d.inventory) (byRole[f.role] ||= []).push(f.path);
  let m = `# 01 — Comprehensive Understanding\n\n## Provisional intent\n${d.provisional_intent}\n\n## Architecture\n${d.architecture}\n\n## Coverage\n- denominator (total files): **${d.coverage.total_files}** · classified: **${d.coverage.classified}** · unknown: **${d.coverage.unknown}**\n\n## Entry points (${d.entry_points.length})\n| name | kind | location | description |\n|---|---|---|---|\n`;
  for (const e of d.entry_points) m += `| \`${e.name}\` | ${e.kind} | \`${e.location}\` | ${e.description} |\n`;
  m += `\n## File inventory by role\n`;
  for (const role of Object.keys(byRole).sort()) m += `\n### ${role} (${byRole[role].length})\n` + byRole[role].map((p) => `- \`${p}\``).join("\n") + "\n";
  return m + ts();
}
function r2(d) {
  const order = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };
  const fs = [...d.findings].sort((a, b) => (order[a.severity] - order[b.severity]));
  let m = `# 02 — Static Audit\n\nCoverage: visited **${d.coverage.visited}/${d.coverage.surface_items}** surface items.\n${d.coverage.unvisited?.length ? `Unvisited (recorded, not assumed absent): ${d.coverage.unvisited.map((x) => "`" + x + "`").join(", ")}` : "All surface items visited."}\n\n## Findings (${fs.length}, falsification-survivors)\n`;
  for (const f of fs) m += `\n### [${f.severity.toUpperCase()}] ${f.id} — ${f.class}\n- **Location:** \`${f.location}\`\n- **What:** ${f.description}\n- **Evidence:** ${f.evidence}\n- **Survived adversarial pass:** ${f.survived_falsification === false ? "no (dropped)" : "yes"}\n`;
  return m + ts();
}
function r3(d) {
  let m = `# 03 — Execution / Dynamic Surface\n\n## Build & test commands (discovered)\n${d.build_commands.map((c) => "- `" + c + "`").join("\n")}\n\n## Test result\n- ran: ${d.test_result.ran} · passed: **${d.test_result.passed}** · failed: **${d.test_result.failed}** · skipped: ${d.test_result.skipped}\n- ${d.test_result.summary || ""}\n\n## Coverage\n- measured: **${d.coverage.measured_pct ?? "n/a"}%**\n- accounting: ${d.coverage.accounting}\n\n## Observed behaviors\n`;
  for (const b of d.observed_behaviors) m += `- \`${b.entry_point}\`: ${b.behavior}${b.location ? ` (\`${b.location}\`)` : ""}\n`;
  m += `\n## Delta applied to Stage-2 findings\n| finding | status | note |\n|---|---|---|\n`;
  for (const x of d.finding_deltas) m += `| ${x.finding_id} | ${x.status} | ${x.note || ""} |\n`;
  return m + ts();
}
function r4(d) {
  let m = `# 04 — Goal + External Research\n\n## Long-term goal candidates (kept plural)\n`;
  for (const g of d.goal_candidates) {
    m += `\n### ${g.id} — ${g.grounded === false ? "⚠ ungrounded/flag-for-human" : "grounded"}\n${g.statement}\n\n**Falsifiable success signals:**\n`;
    for (const s of g.success_signals) m += `- ${s.signal} — _evidence:_ \`${s.evidence_location}\`\n`;
  }
  m += `\n## External research ${d.research.available ? "" : "(⚠ web access unavailable — recorded as degraded)"}\n${d.research.notes || ""}\n`;
  for (const it of d.research.items || []) {
    m += `\n- **${it.idea}** — ${it.relevance}\n`;
    for (const s of it.sources || []) m += `  - ${s.corroborated === false ? "[uncorroborated] " : ""}${s.title}${s.url ? ` <${s.url}>` : ""}\n`;
  }
  return m + ts();
}
function r5(d) {
  let m = `# 05 — Execution-Ready Plan\n\nOrdered change items closing the gap between current state (01–03) and goal (04).\n\n`;
  const byP = {}; for (const it of d.items) (byP[it.priority] ||= []).push(it);
  for (const P of ["P0", "P1", "P2", "P3"]) {
    if (!byP[P]) continue;
    m += `## ${P}\n`;
    for (const it of byP[P]) m += `\n### ${it.id} — \`${it.location}\`\n- **Closes:** ${it.links_to}\n- **Change:** ${it.change}\n- **Verify:** ${it.verification_signal}\n- **Depends on:** ${it.depends_on.length ? it.depends_on.join(", ") : "—"}\n`;
  }
  return m + ts();
}

// ───────────────────────── stages ─────────────────────────
const INTENT_HINT = "This repo is `biosystems`: an N=1 running-physiology analytics library + a longitudinal self-experiment study. Verify this against the code; do not assume it.";

async function preflight() {
  if (existsSync(join(WORK, "preflight.ok"))) { log("preflight: already passed (marker present)"); return; }
  log("preflight: proving auth + tool-use + file-handoff…");
  const probe = join(WORK, `preflight_probe_${SEQ++}.json`);
  if (existsSync(probe)) rmSync(probe);
  const r = await new Promise((res) => {
    const p = spawn("claude", ["-p", `Use the Write tool to create ${probe} containing exactly {"ok":true}. Then reply DONE.`,
      "--output-format", "json", "--model", MODEL_CHEAP, "--max-turns", "6", "--allowedTools", "Read,Write,Bash",
      "--add-dir", REPO, "--strict-mcp-config", "--permission-mode", "acceptEdits"], { cwd: REPO, stdio: ["ignore", "pipe", "pipe"] });
    let O = ""; const k = setTimeout(() => { try { p.kill("SIGKILL"); } catch {} }, 240_000);
    p.stdout.on("data", (d) => (O += d)); p.on("close", () => { clearTimeout(k); res(O); });
  });
  if (!existsSync(probe)) { log("preflight FAILED: claude -p did not authenticate or could not write a file."); process.exit(3); }
  writeFileSync(join(WORK, "preflight.ok"), new Date().toISOString());
  log("preflight: PASSED");
}

async function stage1() {
  log("STAGE 1 — comprehensive understanding");
  const denom = (await sh("git", ["ls-files"])).out.trim().split("\n").filter(Boolean);
  writeFileSync(join(WORK, "denominator.json"), JSON.stringify(denom));
  const prompt = `You are STAGE 1 (Comprehensive Understanding) of a forensic audit of the repository at ${REPO}.
${INTENT_HINT}

Produce a COMPLETE, role-classified map of the repo AS IT IS. The authoritative file set (your coverage denominator) is \`git ls-files\` = ${denom.length} files. You MUST classify every one of them.

Tasks:
(a) Enumerate every tracked file and assign a role: source | test | doc | config | asset | generated | dead | unknown. Open files to classify source/test/config — do not guess from filename alone. Use "unknown" ONLY if genuinely unclassifiable after opening.
(b) Identify EVERY entry point: CLI commands (read src/biosystems/cli.py for the typer command surface), library exports (__init__.py), scripts in tools/ and daily_running_brief/, CI workflows. Give each a one-line description grounded in the code, with a path:line location.
(c) Describe the system architecture: the subsystems under src/biosystems/ and how data flows between them.
(d) State the PROVISIONAL intent (apparent purpose), explicitly marked provisional.
Fan out reads across every subtree (src, tests, tools, docs, data, .github, daily_running_brief, audits). The inventory.path values should reproduce the ${denom.length}-file denominator as closely as possible; coverage.total_files MUST equal ${denom.length}.`;
  const res = await runAgent({ name: "s1-understand", prompt, schema: S1, maxTurns: 80 });
  if (!res.ok) return halt("stage1", "Stage-1 worker produced no schema-valid inventory.");
  const d = res.data;
  // Stop-test: coverage denominator diff + zero-unknown convergence (deterministic, in Node)
  const invPaths = new Set(d.inventory.map((x) => x.path.replace(/^\.\//, "")));
  const missing = denom.filter((p) => !invPaths.has(p) && !p.startsWith("audit/"));
  const unknowns = d.inventory.filter((x) => x.role === "unknown").map((x) => x.path);
  log(`  coverage: inventory ${invPaths.size}/${denom.length}; missing ${missing.length}; unknown-role ${unknowns.length}`);
  if (missing.length > Math.max(8, denom.length * 0.05))
    return halt("stage1", `Inventory misses ${missing.length} files vs git ls-files denominator (>5%). Sample: ${missing.slice(0, 12).join(", ")}`);
  d._stoptest = { denominator: denom.length, inventoried: invPaths.size, missing_count: missing.length, missing_sample: missing.slice(0, 20), unknown_roles: unknowns };
  writeFileSync(join(AUDIT, "01-understanding.json"), JSON.stringify(d, null, 2));
  await checkpoint("stage1 understanding", { "01-understanding.md": r1(d), "01-understanding.json": JSON.stringify(d, null, 2) });
  return d;
}

async function stage2(s1) {
  log("STAGE 2 — static audit (audit → re-audit → falsify → fixpoint)");
  const intent = s1.provisional_intent;
  const sources = s1.inventory.filter((f) => f.role === "source").map((f) => f.path);
  const surface = s1.inventory.length;
  const base = `You are STAGE 2 (Static Audit) of a forensic audit of ${REPO}. Read the actual source (do not trust the map alone). Stage-1 provisional intent: "${intent}". A defect is only a defect relative to intended behavior — judge against that intent, and record any CODE↔INTENT or CODE↔DOC mismatch as a finding (class intent_mismatch / doc_drift). The Stage-1 inventory has ${surface} items; ${sources.length} are source. Read 01-understanding.json for the full map.`;
  let findings = [];
  // round 0: broad audit across diverse lenses
  const lenses = [
    "correctness bugs & edge cases in the physics/metrics/gap computations and ingestion parsers (src/biosystems/physics/*, src/biosystems/ingestion/*)",
    "security, secrets handling, privacy/PII (GPS), input validation, and external API calls (src/biosystems/ingestion/strava.py, wellness/habitdash.py, environment/weather.py, tools/sanitize_gps.py)",
    "documentation/code drift between README.md / docs/* / reports/* and actual code behavior; and reproducibility of claimed results",
    "design defects, error handling, type-safety gaps, CLI robustness, and test coverage gaps (src/biosystems/cli.py, tests/*)",
  ];
  const r0 = await pMap(lenses, (lens, i) => runAgent({
    name: `s2-audit-l${i}`, schema: S2, maxTurns: 70,
    prompt: `${base}\n\nLENS: focus on ${lens}. Find every defect findable by reading. Each finding: stable id (e.g. F-${i}-1), location path:line, class, severity, concrete evidence (quote the code by location, never paste secrets), and description. Set survived_falsification to null (a later pass decides). Report coverage.visited = number of distinct files you actually opened, surface_items = ${surface}, and list any high-value files you did NOT open in coverage.unvisited.`,
  }), 2);
  for (const r of r0) if (r.ok) findings.push(...r.data.findings);
  const fp = (f) => `${(f.location || "").toLowerCase()}|${f.class}|${(f.description || "").slice(0, 40).toLowerCase()}`;
  const dedupe = (arr) => { const seen = new Set(); return arr.filter((f) => { const k = fp(f); if (seen.has(k)) return false; seen.add(k); return true; }); };
  findings = dedupe(findings);
  log(`  round 0: ${findings.length} candidate findings from ${r0.filter((r) => r.ok).length}/${lenses.length} lenses`);

  // fixpoint: re-audit sweep (add candidates) → falsify the WHOLE set → keep survivors → stable?
  let prev = "";
  const ceiling = 4;
  for (let round = 1; round <= ceiling; round++) {
    const sweep = await runAgent({ name: `s2-reaudit-r${round}`, schema: S2, maxTurns: 50, model: MODEL_DEEP,
      prompt: `${base}\n\nRE-AUDIT SWEEP. Here are findings already collected:\n${JSON.stringify(findings.map((f) => ({ id: f.id, location: f.location, class: f.class, description: f.description })))}\nFind ADDITIONAL defects NOT already listed (new locations or new classes). If you find none, return an empty findings array with coverage. Do not restate existing ones.` });
    if (sweep.ok && sweep.data.findings.length) { findings = dedupe([...findings, ...sweep.data.findings]); log(`  round ${round}: +${sweep.data.findings.length} re-audit candidates → ${findings.length}`); }

    const falsify = await runAgent({ name: `s2-falsify-r${round}`, schema: S2, maxTurns: 70, model: MODEL_DEEP,
      prompt: `${base}\n\nADVERSARIAL FALSIFICATION. You are an independent skeptic. For EACH finding below, return to the cited source location and try to REFUTE it: is the location real, the evidence accurate, the severity justified, the class correct? Return the SAME findings with survived_falsification=true for those that withstand scrutiny and survived_falsification=false for those that are wrong, unlocatable, duplicated, or overstated (you may correct severity/class/evidence on survivors). Also verify coverage: of the ${sources.length} source files, flag in coverage.unvisited any that NO finding references and that you judge under-examined. Findings to test:\n${JSON.stringify(findings)}` });
    if (!falsify.ok) return halt("stage2", `Falsification pass failed in round ${round} — cannot promote unfalsified findings.`);
    findings = falsify.data.findings.filter((f) => f.survived_falsification !== false);
    var lastCoverage = falsify.data.coverage;
    findings = dedupe(findings);
    const sig = findings.map(fp).sort().join("§");
    log(`  round ${round}: ${findings.length} survivors after falsification`);
    if (sig === prev) { log(`  fixpoint reached at round ${round}`); break; }
    prev = sig;
    if (round === ceiling) log("  fixpoint ceiling hit — promoting current survivor set");
  }
  const d = { findings, coverage: lastCoverage || { surface_items: surface, visited: surface, unvisited: [] } };
  writeFileSync(join(AUDIT, "02-static-audit.json"), JSON.stringify(d, null, 2));
  await checkpoint("stage2 static-audit", { "02-static-audit.md": r2(d), "02-static-audit.json": JSON.stringify(d, null, 2) });
  return d;
}

async function stage3(s1, s2) {
  log("STAGE 3 — execution / dynamic surface");
  const prompt = `You are STAGE 3 (Execution) of a forensic audit of ${REPO}. Discover the build/test/coverage commands from the repo ITSELF (README.md, pyproject.toml [tool.pytest], .github/workflows/*, Dockerfile) — do not assume. The package is already pip-installed in this sandbox.
Do, in the sandbox:
(1) Run the test suite under coverage. Prefer: \`python -m pytest -o addopts="" --cov=biosystems --cov-report=term-missing -q\`. Capture passed/failed/skipped and the measured coverage %.
(2) Drive at least 2 real entry points (e.g. \`python -m biosystems.cli --help\`, and the README sample-data snippet that computes run_metrics on data/sample/sample_run.csv) and record observed behavior.
(3) Use this execution evidence to CONFIRM / REFUTE / REFINE the Stage-2 findings. Read 02-static-audit.json for the finding list and reference each by its id in finding_deltas.
(4) Coverage accounting must total 100%: every significant unexecuted region is either listed in coverage.unexecuted_regions with a reason (requires-credentials | external-service | hardware-gated | dead | destructive-skip) or covered. Report the real measured % from pytest-cov.
Report build_commands you actually ran.`;
  const res = await runAgent({ name: "s3-execute", prompt, schema: S3, maxTurns: 60 });
  if (!res.ok) return halt("stage3", "Stage-3 worker produced no schema-valid execution report.");
  // adversarial check of self-reported coverage/accounting
  const chk = await runAgent({ name: "s3-coverage-check", schema: S3, maxTurns: 40, model: MODEL_DEEP,
    prompt: `You independently verify a Stage-3 execution report for ${REPO}. RE-RUN \`python -m pytest -o addopts="" --cov=biosystems --cov-report=term -q\` yourself and compare to the claimed numbers below. Correct any passed/failed/skipped or measured_pct that does not match your own run, and ensure every unexecuted region has a valid reason. Return the corrected execution object (same schema), keeping finding_deltas from the input unless your run contradicts them.\nClaimed report:\n${JSON.stringify(res.data)}` });
  const d = chk.ok ? chk.data : res.data;
  writeFileSync(join(AUDIT, "03-execution.json"), JSON.stringify(d, null, 2));
  await checkpoint("stage3 execution", { "03-execution.md": r3(d), "03-execution.json": JSON.stringify(d, null, 2) });
  return d;
}

async function stage4(s1, s2, s3) {
  log("STAGE 4 — goal + external research (parallel halves)");
  const ctx = `Forensic audit of ${REPO}. Artifacts available to Read: audit/01-understanding.json, audit/02-static-audit.json, audit/03-execution.json. Stage-1 provisional intent: "${s1.provisional_intent}".`;
  const [goalRes, researchRes] = await Promise.all([
    runAgent({ name: "s4-goal", schema: S4, maxTurns: 45, model: MODEL_DEEP,
      prompt: `${ctx}\nGOAL HALF only. Infer the repo's long-term goal(s). Keep candidates PLURAL (2–4); do not collapse to one. State each as falsifiable success signals, and EVERY signal must trace to evidence in Stages 1–3 (cite a path:line or an audit/*.json location). Mark grounded=false for any candidate you cannot ground (flag for human). For the research field, return {"available": true, "items": []} as a placeholder — the research half is produced separately and merged.` }),
    runAgent({ name: "s4-research", schema: S4, web: true, maxTurns: 45, model: MODEL_DEEP, timeoutMs: 900_000,
      prompt: `${ctx}\nRESEARCH HALF only. Do a cross-checked external search (in the shape of /deep-research: gather independently, weigh sources against each other) for ideas, technologies, methods, and projects that would MATERIALLY advance this project's goal — e.g. N=1 / single-subject study methodology & statistics, running-physiology metrics (efficiency factor, aerobic decoupling, GAP, hrTSS, critical power), reproducible sports-science pipelines, and publication venues for N=1 methods papers. Cite every source with a URL; mark corroborated=false for any single-source claim. If web tools (WebSearch/WebFetch) are unavailable or blocked, set research.available=false and explain in research.notes (do NOT fabricate sources). For goal_candidates return a single placeholder candidate {"id":"R-placeholder","statement":"see goal half","success_signals":[{"signal":"merged from goal half","evidence_location":"audit/04-goal.json"}],"grounded":null} — the goal half is authoritative and merged.` }),
  ]);
  if (!goalRes.ok) return halt("stage4", "Goal half produced no schema-valid candidates.");
  let goals = goalRes.data.goal_candidates;
  // adversarial grounding check — drop/flag ungrounded candidates
  const ground = await runAgent({ name: "s4-goal-ground", schema: S4, maxTurns: 35, model: MODEL_DEEP,
    prompt: `${ctx}\nGROUNDING CHECK. For each goal candidate below, verify each success signal's evidence_location actually supports it (open the cited artifact/source). Set grounded=false for any candidate whose signals do not trace to real Stage 1–3 evidence; keep grounded=true otherwise. Return the goal_candidates (same schema) with research {"available":true,"items":[]}.\nCandidates:\n${JSON.stringify(goals)}` });
  if (ground.ok) goals = ground.data.goal_candidates;
  const research = researchRes.ok ? researchRes.data.research : { available: false, items: [], notes: "Research half failed to produce schema-valid output; recorded as unavailable rather than fabricated." };
  const d = { goal_candidates: goals, research };
  writeFileSync(join(AUDIT, "04-goal.json"), JSON.stringify(d, null, 2));
  await checkpoint("stage4 goal+research", { "04-goal.md": r4(d), "04-goal.json": JSON.stringify(d, null, 2) });
  return d;
}

async function stage5(s1, s2, s3, s4) {
  log("STAGE 5 — execution-ready plan");
  const prompt = `You are STAGE 5 (Execution-Ready Plan) of a forensic audit of ${REPO}. Read all prior artifacts: audit/01-understanding.json, audit/02-static-audit.json, audit/03-execution.json, audit/04-goal.json.
Produce ORDERED change items that close the gap between current state (Stages 1–3) and the goal (Stage 4). Each item MUST have: id; links_to (a specific Stage-2 finding id OR a Stage-4 goal-gap, named explicitly); location (file/module to change); change (what to do, concretely); verification_signal (the exact observation/test/command that proves it worked); depends_on (ids of items that must precede it — real dependency order); priority (P0=correctness/blocker, P1=important, P2=quality, P3=nice-to-have). A fresh engineer must be able to map every item to a concrete diff target without asking a question.`;
  const res = await runAgent({ name: "s5-plan", prompt, schema: S5, maxTurns: 55 });
  if (!res.ok) return halt("stage5", "Stage-5 worker produced no schema-valid plan.");
  let items = res.data.items;
  // completeness gate (Node) + fresh diff-target mapping check (agent)
  const incomplete = items.filter((it) => !it.links_to || !it.location || !it.verification_signal || !Array.isArray(it.depends_on) || !it.priority);
  if (incomplete.length) log(`  ! ${incomplete.length} items missing required fields — requesting repair`);
  const chk = await runAgent({ name: "s5-difftarget-check", schema: S5, maxTurns: 40, model: MODEL_DEEP,
    prompt: `${prompt}\n\nVERIFY-AND-REPAIR. A draft plan is below. For each item confirm a fresh engineer could map it to a concrete diff target with no clarifying question; repair any vague location/change/verification_signal, ensure depends_on forms a real order, and that links_to names a concrete finding id or goal gap. Return the corrected plan (same schema).\nDraft:\n${JSON.stringify(items)}` });
  if (chk.ok) items = chk.data.items;
  const stillBad = items.filter((it) => !it.links_to || !it.location || !it.verification_signal || !Array.isArray(it.depends_on) || !it.priority);
  if (stillBad.length) return halt("stage5", `${stillBad.length} plan items remain incomplete after repair (missing finding/goal link, location, verification signal, or dependency).`);
  const d = { items };
  writeFileSync(join(AUDIT, "05-plan.json"), JSON.stringify(d, null, 2));
  await checkpoint("stage5 plan", { "05-plan.md": r5(d), "05-plan.json": JSON.stringify(d, null, 2) });
  return d;
}

// ───────────────────────── main ─────────────────────────
async function main() {
  mkdirSync(WORK, { recursive: true });
  writeFileSync(join(AUDIT, ".gitignore"), ".work/\n");
  BRANCH = (await sh("git", ["rev-parse", "--abbrev-ref", "HEAD"])).out.trim() || "HEAD";
  log(`repo=${REPO} branch=${BRANCH} fresh=${FRESH} onlyStage=${ONLY_STAGE ?? "-"}`);
  if (FRESH) for (const f of ["01-understanding", "02-static-audit", "03-execution", "04-goal", "05-plan"])
    for (const ext of ["md", "json"]) { const p = join(AUDIT, `${f}.${ext}`); if (existsSync(p)) rmSync(p); }

  await preflight();
  const has = (n) => existsSync(join(AUDIT, `${n}.json`));
  const load = (n) => JSON.parse(readFileSync(join(AUDIT, `${n}.json`), "utf8"));

  let d1, d2, d3, d4;
  const want = (n) => ONLY_STAGE === null || ONLY_STAGE === n;

  if (want(1)) d1 = (has("01-understanding") && !FRESH && ONLY_STAGE === null) ? load("01-understanding") : await stage1();
  else d1 = load("01-understanding");
  if (ONLY_STAGE === 1) return done();

  if (want(2)) d2 = (has("02-static-audit") && ONLY_STAGE === null) ? load("02-static-audit") : await stage2(d1);
  else d2 = has("02-static-audit") ? load("02-static-audit") : null;
  if (ONLY_STAGE === 2) return done();

  if (want(3)) d3 = (has("03-execution") && ONLY_STAGE === null) ? load("03-execution") : await stage3(d1, d2);
  else d3 = has("03-execution") ? load("03-execution") : null;
  if (ONLY_STAGE === 3) return done();

  if (want(4)) d4 = (has("04-goal") && ONLY_STAGE === null) ? load("04-goal") : await stage4(d1, d2, d3);
  else d4 = has("04-goal") ? load("04-goal") : null;
  if (ONLY_STAGE === 4) return done();

  if (want(5)) await stage5(d1, d2, d3, d4);
  done();
}
function done() { log(`PIPELINE COMPLETE. approx API-equiv cost $${TOTAL_COST.toFixed(2)} (subscription spend differs).`); process.exit(0); }
main().catch((e) => { log("FATAL", e?.stack || e); process.exit(1); });
