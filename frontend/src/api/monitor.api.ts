import { httpClient } from '@/api/http'
import type { MonitorHealthResponse } from '@/types/api.types'

export async function getHealthCheck(): Promise<MonitorHealthResponse> {
  const { data } = await httpClient.get<MonitorHealthResponse>('/api/v1/')
  return data
}
