/* AUTO-GENERATED from packages/shared-schemas/requirements.schema.json. DO NOT EDIT. */

/**
 * Dataset A: Formal schema for system requirements and operational constraints
 */
export interface ADIP_Requirements_Schema {
  /**
   * Unique identifier for the project
   */
  project_id: string;
  domain: "e-commerce" | "fintech" | "social_network" | "streaming" | "iot" | "healthcare" | "saas";
  users: number;
  concurrency: number;
  rps: number;
  peak_rps: number;
  /**
   * Data volume in Gigabytes (GB)
   */
  data_size: number;
  /**
   * Ratio of read traffic to total traffic between 0.0 and 1.0
   */
  read_write_ratio: number;
  /**
   * Maximum permissible latency in milliseconds
   */
  latency_sla: number;
  /**
   * Required uptime percentage (e.g., 99.9)
   */
  availability_sla: number;
  /**
   * Monthly infrastructure budget in USD
   */
  budget: number;
  /**
   * Projected annual growth percentage
   */
  traffic_growth?: number;
  team_size?: number;
}
