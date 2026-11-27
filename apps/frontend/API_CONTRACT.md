# Proposed API contracts (frontend, Step 8)

STATUS: PROPOSED by the frontend. Not agreed with the backend/ML owners yet.
Types live in `src/types/proposed.ts`; the mock server (`src/mocks/handlers.ts`) implements them.
Once agreed, move them to `packages/shared-schemas/` and generate the types like the others.

All three responses carry `data_origin: "simulated" | "measured" | "predicted"` so the UI can label numbers honestly.

## POST /api/v1/recommendations
Request: `{ "weights": { "latency": 35, "cost": 25, "scalability": 20, "reliability": 20 } }`
(non-negative; scaled to 100% by the server; all-zero or negative -> 422).
Response: `{ method: "topsis", weights_used, excluded_criteria, ranking: [{ architecture_id, rank, closeness, values, feasible, violations }], recommended_id, data_origin }`
`recommended_id` = best-ranked option that meets the latency SLA and budget.

## GET /api/v1/explanations?architecture_id=...&target=latency_p95_ms|monthly_cost_usd
Response: `{ architecture_id, target, base_value, prediction, contributions: [{ feature, value, shap_value }], data_origin, model_version? }`
Additivity: `base_value + sum(shap_value)` should equal `prediction`; the UI shows any gap as "All other features". 404 for unknown architecture/target.

## POST /api/v1/what-if
Request: `{ "scenario": { rps, concurrency, data_size, read_write_ratio, replica_count, cpu_limit, memory_limit, database, cache, messaging, cloud } }`
Response: `{ scenario, predictions, data_origin }` where `predictions` has the same shape as one item of `/predictions`.

## Open questions for the backend / ML owner
1. TOPSIS criteria: the UI maps latency -> p95, cost -> monthly cost, scalability -> headroom, reliability -> error rate. Is that right, and which fields supply them?
2. Should the weights/ranking be computed server-side (as proposed) or client-side from `/predictions`? The frontend has a reference TOPSIS (`features/recommendation/topsis.ts`) with tests.
3. What-if currently models a single architecture. Should the request name the architecture?
4. Which SHAP targets will the trained models actually support?
