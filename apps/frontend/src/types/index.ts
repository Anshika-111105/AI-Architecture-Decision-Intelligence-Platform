// Friendly aliases over the generated schema types.
export type { ADIP_Requirements_Schema as Requirements } from './generated/requirements'
export type { ADIP_Architecture_Schema as Architecture } from './generated/architecture'
export type { ADIP_Prediction_Output_Schema as PredictionResult } from './generated/prediction'

// Provenance label required by the research-integrity rules (README section 45):
// simulated/synthetic numbers must never be shown as real-world ground truth.
export type DataOrigin = 'observed' | 'benchmark' | 'experimental' | 'simulated' | 'synthetic'
