import { request } from "./http";

export interface HealthStatus {
  status: string;
  app: string;
}

export const healthApi = {
  check: () => request<HealthStatus>("/health"),
};

export async function getHealth(): Promise<HealthStatus> {
  return healthApi.check();
}
