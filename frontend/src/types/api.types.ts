import axios from 'axios'

export interface ApiErrorResponse {
  trace_id: string
  message: string
}

export interface MonitorHealthResponse {
  name: string
  version: string
}

export function extractApiError(error: unknown): ApiErrorResponse {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as Partial<ApiErrorResponse> | undefined
    if (data && typeof data.message === 'string') {
      return {
        trace_id: typeof data.trace_id === 'string' ? data.trace_id : 'http-error',
        message: data.message,
      }
    }
    return {
      trace_id: `http-${error.response?.status ?? 'network'}`,
      message: error.message || 'Network request failed',
    }
  }
  if (error instanceof Error) {
    return { trace_id: 'client-error', message: error.message }
  }
  return { trace_id: 'unknown-error', message: 'An unexpected error occurred' }
}
