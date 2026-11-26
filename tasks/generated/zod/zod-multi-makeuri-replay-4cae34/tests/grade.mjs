// Turns the vitest JSON report into Harbor rewards.
//
// reward = 1 only when every test in f2p.txt passes (the feature works) and
// every test in p2p.txt passes (nothing else regressed). Both lists are
// recorded by the factory: f2p = tests that pass with the reference solution
// but not on the untouched task; p2p = tests that pass on both.
import fs from "node:fs";
import path from "node:path";

const LOGS = "/logs/verifier";
const ROOT = "/app/packages/zod";

const readList = (file) =>
  fs.existsSync(file)
    ? fs.readFileSync(file, "utf8").split("\n").map((s) => s.replace(/\s+/g, " ").trim()).filter(Boolean)
    : [];

const results = {};
const reportPath = path.join(LOGS, "vitest.json");
if (fs.existsSync(reportPath)) {
  const report = JSON.parse(fs.readFileSync(reportPath, "utf8"));
  for (const file of report.testResults ?? []) {
    const rel = path.relative(ROOT, file.name);
    for (const t of file.assertionResults ?? []) {
      // normalise whitespace: some upstream test names end with a space
      const id = `${rel} > ${t.fullName}`.replace(/\s+/g, " ").trim();
      // a test reported twice (runtime + typecheck) passes only if both pass
      results[id] = results[id] && results[id] !== "passed" ? results[id] : t.status;
    }
  }
}
fs.writeFileSync(path.join(LOGS, "results.json"), JSON.stringify(results, null, 1));

const f2p = readList("/tests/f2p.txt");
const p2p = readList("/tests/p2p.txt");
const passed = (id) => results[id] === "passed";
const f2pPassed = f2p.filter(passed).length;
const p2pBroken = p2p.filter((id) => !passed(id));

const rewards = {
  reward: f2p.length > 0 && f2pPassed === f2p.length && p2p.length > 0 && p2pBroken.length === 0 ? 1 : 0,
  feature_pass_rate: f2p.length ? Number((f2pPassed / f2p.length).toFixed(4)) : 0,
  feature_tests: f2p.length,
  regression_ok: p2p.length > 0 && p2pBroken.length === 0 ? 1 : 0,
  p2p_tests: p2p.length,
  p2p_broken: p2pBroken.length,
};
fs.writeFileSync(path.join(LOGS, "reward.json"), JSON.stringify(rewards));
fs.writeFileSync(path.join(LOGS, "p2p_broken.txt"), p2pBroken.join("\n"));
console.log(JSON.stringify(rewards, null, 2));
