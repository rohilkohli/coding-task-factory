// Per-defect partial credit for multi-bug tasks (Node version of partial_credit.py).
// For each injected defect, /tests/defects.json lists the tests it breaks on its
// own; a defect counts as fixed when all of them pass. The binary `reward` is
// unchanged; defects_fixed, defects_total, partial_credit and defect_<i>_fixed
// are added to reward.json, and details go to partial_credit.json.
import fs from "node:fs";

const LOGS = "/logs/verifier";
const norm = (t) => t.replace(/\s+/g, " ").trim();
const readJson = (p, fallback) => (fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, "utf8")) : fallback);

const raw = readJson(`${LOGS}/results.json`, {});
const results = Object.fromEntries(Object.entries(raw).map(([k, v]) => [norm(k), v]));
const reward = readJson(`${LOGS}/reward.json`, { reward: 0 });
const defects = readJson("/tests/defects.json", []);
const fixed = defects.map((d) => (d.tests.length > 0 && d.tests.every((t) => results[norm(t)] === "passed") ? 1 : 0));
const total = fixed.reduce((a, b) => a + b, 0);
Object.assign(reward, {
  defects_total: defects.length,
  defects_fixed: total,
  partial_credit: defects.length ? Number((total / defects.length).toFixed(4)) : 0,
});
fixed.forEach((f, i) => { reward[`defect_${i + 1}_fixed`] = f; });
fs.writeFileSync(`${LOGS}/reward.json`, JSON.stringify(reward));
fs.writeFileSync(`${LOGS}/partial_credit.json`,
  JSON.stringify({ defects: defects.map((d, i) => ({ ...d, fixed: Boolean(fixed[i]) })) }, null, 1));
console.log(JSON.stringify({ defects_fixed: total, defects_total: defects.length, partial_credit: reward.partial_credit }));
