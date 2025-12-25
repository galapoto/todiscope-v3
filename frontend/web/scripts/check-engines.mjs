import process from "node:process";

const DEFAULT_BASE_URL = "http://localhost:8400";
const ALL_ENGINES = [
  "csrd",
  "financial-forensics",
  "cost-intelligence",
  "audit-readiness",
  "enterprise-capital-debt-readiness",
  "data-migration-readiness",
  "erp-integration-readiness",
  "enterprise-deal-transaction-readiness",
  "litigation-analysis",
  "regulatory-readiness",
  "enterprise-insurance-claim-forensics",
  "distressed-asset-debt-stress",
];

const REPORT_ENGINES = new Set([
  "financial-forensics",
  "cost-intelligence",
  "enterprise-capital-debt-readiness",
  "enterprise-deal-transaction-readiness",
  "litigation-analysis",
]);

function backendEngineIdToSlug(engineId) {
  const overrides = {
    engine_construction_cost_intelligence: "cost-intelligence",
    engine_enterprise_litigation_dispute: "litigation-analysis",
  };
  if (overrides[engineId]) return overrides[engineId];
  if (!engineId.startsWith("engine_")) return null;
  return engineId.slice("engine_".length).replaceAll("_", "-");
}

function readArg(flag, fallback) {
  const idx = process.argv.indexOf(flag);
  if (idx === -1) return fallback;
  const value = process.argv[idx + 1];
  if (!value || value.startsWith("--")) return fallback;
  return value;
}

const baseUrl = readArg("--base", DEFAULT_BASE_URL).replace(/\/+$/, "");
const apiKey = readArg("--api-key", process.env.NEXT_PUBLIC_API_KEY || "");
const checkAll = process.argv.includes("--all");

async function fetchJson(path) {
  const response = await fetch(`${baseUrl}${path}`, {
    headers: apiKey ? { "X-API-Key": apiKey } : {},
  });
  const text = await response.text();
  let json = null;
  try {
    json = JSON.parse(text);
  } catch {
    json = null;
  }
  return { ok: response.ok, status: response.status, json, text };
}

async function probe(path) {
  try {
    const response = await fetch(`${baseUrl}${path}`, {
      method: "GET",
      headers: apiKey ? { "X-API-Key": apiKey } : {},
    });
    const status = response.status;
    const exists = status !== 404;
    return { path, status, exists, ok: response.ok };
  } catch (error) {
    return {
      path,
      status: 0,
      exists: false,
      ok: false,
      error: error instanceof Error ? error.message : "Network error",
    };
  }
}

function fmt(result) {
  if (result.error) return `❌ ${result.path} (network error: ${result.error})`;
  if (!result.exists) return `❌ ${result.path} (404)`;
  if (result.ok) return `✅ ${result.path} (${result.status})`;
  return `⚠️ ${result.path} (${result.status})`;
}

async function main() {
  const enabled = await fetchJson("/api/v3/engine-registry/enabled");
  if (!enabled.ok || !enabled.json?.enabled_engines) {
    console.error(
      `Failed to read enabled engines from ${baseUrl}/api/v3/engine-registry/enabled (status ${enabled.status})`
    );
    process.exit(2);
  }

  const engines = checkAll
    ? ALL_ENGINES
    : enabled.json.enabled_engines
        .map(backendEngineIdToSlug)
        .filter((id) => Boolean(id));
  console.log(`Backend: ${baseUrl}`);
  console.log(`${checkAll ? "All engines" : "Enabled engines"}: ${engines.length}`);

  let missing = 0;

  for (const engineId of engines) {
    console.log(`\n== ${engineId} ==`);
    const [run, report] = await Promise.all([
      probe(`/api/v3/engines/${engineId}/run`),
      REPORT_ENGINES.has(engineId)
        ? probe(`/api/v3/engines/${engineId}/report`)
        : Promise.resolve(null),
    ]);
    console.log(fmt(run));
    if (report) console.log(fmt(report));
    else console.log(`— /api/v3/engines/${engineId}/report (not required)`);

    if (!run.exists) missing++;
    if (report && !report.exists) missing++;
  }

  if (missing) {
    console.error(
      `\n${checkAll ? "WARN" : "FAIL"}: ${missing} missing endpoints (404).`
    );
    process.exit(checkAll ? 0 : 1);
  }

  console.log(
    `\nOK: all ${checkAll ? "listed" : "enabled"} engines have run/report endpoints (non-404).`
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(2);
});
