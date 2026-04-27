"""End-to-end smoke test for the Ceyel API."""
import urllib.request, json, sys, time

BASE = "http://127.0.0.1:8000"
PASSES = []
FAILS  = []

def get(path):
    with urllib.request.urlopen(BASE + path, timeout=10) as r:
        return json.loads(r.read())

def post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        BASE + path, data=body,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

def check(label, condition, detail=""):
    if condition:
        PASSES.append(label)
        print(f"  [PASS] {label} {detail}")
    else:
        FAILS.append(label)
        print(f"  [FAIL] {label} {detail}")

print("=" * 50)
print("  Ceyel End-to-End API Test")
print("=" * 50)

# 1 - Bulk ingest sample events
with open("data/sample_events.json") as f:
    events = json.load(f)
r = post("/api/events/bulk", events)
check("Bulk ingest", r["ingested"] > 0, f"({r['ingested']} ingested, {r['failed']} failed)")

# 2 - Stats
s = get("/api/mining/stats")
check("Mining stats", s["total_events"] > 0, f"({s['total_events']} events, {s['total_cases']} cases)")

# 3 - DFG
dfg = get("/api/mining/dfg")
check("DFG nodes", len(dfg["nodes"]) > 0, f"({len(dfg['nodes'])} nodes, {len(dfg['edges'])} edges)")

# 4 - Variants
v = get("/api/mining/variants")
check("Variants", len(v) > 0, f"({len(v)} variants)")

# 5 - Cycle time
ct = get("/api/mining/cycle-time")
check("Cycle time", ct["average_hours"] >= 0, f"(avg={ct['average_hours']}h)")

# 6 - Conformance
c = post("/api/conformance/check", {
    "reference_sequence": [
        "Application Received", "Document Verification",
        "Credit Check", "Risk Assessment",
        "Approval Decision", "Loan Disbursement"
    ]
})
check("Conformance", "fitness_score" in c, f"(fitness={c.get('fitness_score')}, deviating={c.get('deviating_cases')})")

# 7 - Prediction
p = get("/api/prediction/LOAN-001")
check("Prediction", "remaining_time_hours" in p, f"(remaining={p.get('remaining_time_hours')}h, risk={p.get('delay_risk_level')})")

# 8 - Merkle root
t = get("/api/trust/root")
check("Merkle root", len(t["merkle_root"]) == 64, f"({t['merkle_root'][:20]}...)")

# 9 - Merkle proof for LOAN-001
pr = get("/api/trust/proof/LOAN-001")
all_valid = all(p["valid"] for p in pr["proofs"])
check("Merkle proofs", all_valid, f"({len(pr['proofs'])} proofs, all_valid={all_valid})")

# 10 - Blockchain commit
b = post("/api/blockchain/commit", {})
check("Block commit", "block" in b, f"(block #{b.get('block', {}).get('block_id')})")

# 11 - Verify chain
v2 = get("/api/blockchain/verify")
check("Chain integrity", v2["valid"], f"(length={v2.get('chain_length')})")

# 12 - Event list
evs = get("/api/events")
check("Event listing", len(evs) > 0, f"({len(evs)} events)")

# 13 - Hash audit
hashes = get("/api/trust/hashes")
check("Hash audit", len(hashes) > 0, f"({len(hashes)} hashes)")

print()
print("=" * 50)
print(f"  Results: {len(PASSES)} passed, {len(FAILS)} failed")
print("=" * 50)
if FAILS:
    sys.exit(1)
