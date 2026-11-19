/* AUTO-GENERATED from packages/shared-schemas/prediction.schema.json. DO NOT EDIT. */

/**
 * Dataset D & ML Inference: Formal schema for ML predictions, percentiles, and SHAP explainability outputs
 */
export interface ADIP_Prediction_Output_Schema {
  architecture_id: string;
  predictions: {
    latency: {
      p50_ms: number;
      p90_ms: number;
      p95_ms: number;
      p99_ms: number;
    };
    throughput: {
      predicted_rps: number;
    };
    resources: {
      cpu_utilization_pct: number;
      memory_utilization_mb: number;
    };
    cost: {
      estimated_monthly_usd: number;
    };
    reliability?: {
      estimated_error_rate_pct?: number;
      availability_score?: number;
    };
    scalability?: {
      max_supported_rps?: number;
      scalability_headroom_multiplier?: number;
    };
  };
  sla_compliance: {
    meets_latency_sla: boolean;
    meets_budget_sla: boolean;
    latency_margin_ms?: number;
    budget_margin_usd?: number;
  };
  explainability: {
    top_contributing_features: {
      feature: string;
      shap_value: number;
      impact: "increases_latency" | "decreases_latency" | "increases_cost" | "decreases_cost";
    }[];
    summary: string;
  };
}
