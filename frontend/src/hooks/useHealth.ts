import { useCallback, useEffect, useState } from "react";
import { dashboardApi } from "../services/api";
import type { HealthStatus } from "../types/dashboard";

export function useHealth() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  const checkHealth = useCallback(async () => {
    try {
      const data = await dashboardApi.getHealth();
      setHealth(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Backend unreachable");
    }
  }, []);

  useEffect(() => {
    void checkHealth();
  }, [checkHealth]);

  return { health, healthError: error, refreshHealth: checkHealth };
}

