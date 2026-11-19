<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { getHealthCheck } from '@/api/monitor.api'
import { extractApiError, type ApiErrorResponse, type MonitorHealthResponse } from '@/types/api.types'

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '')
const swaggerUrl = `${apiBaseUrl}/swagger/`

const health = ref<MonitorHealthResponse | null>(null)
const loading = ref(false)
const apiError = ref<ApiErrorResponse | null>(null)

async function loadHealth(): Promise<void> {
  loading.value = true
  apiError.value = null
  try {
    health.value = await getHealthCheck()
  } catch (err) {
    health.value = null
    apiError.value = extractApiError(err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadHealth()
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">System Dashboard</h1>
        <p class="mt-1 text-sm text-slate-500">
          Live health status and quick access to Clean Architecture API modules.
        </p>
      </div>
      <button
        type="button"
        :disabled="loading"
        class="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        @click="loadHealth"
      >
        {{ loading ? 'Checking...' : 'Refresh Health' }}
      </button>
    </div>

    <div class="grid gap-4 md:grid-cols-3">
      <div class="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
        <p class="text-xs font-semibold uppercase tracking-wider text-slate-500">API Status</p>
        <div class="mt-2 flex items-center gap-2">
          <span
            :class="[
              'inline-block h-2.5 w-2.5 rounded-full',
              health ? 'bg-emerald-500' : apiError ? 'bg-rose-500' : 'bg-slate-300',
            ]"
          />
          <span class="text-lg font-bold text-slate-900">
            {{ health ? 'Online' : apiError ? 'Unreachable' : 'Checking...' }}
          </span>
        </div>
        <p v-if="apiError" class="mt-2 text-xs text-rose-600">
          [{{ apiError.trace_id }}] {{ apiError.message }}
        </p>
        <p v-else class="mt-2 font-mono text-xs text-slate-500">{{ apiBaseUrl }}/api/v1/</p>
      </div>

      <div class="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
        <p class="text-xs font-semibold uppercase tracking-wider text-slate-500">Application Name</p>
        <p class="mt-2 text-lg font-bold text-slate-900">{{ health?.name || '—' }}</p>
        <p class="mt-2 text-xs text-slate-500">Reported by Monitor HealthCheck</p>
      </div>

      <div class="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
        <p class="text-xs font-semibold uppercase tracking-wider text-slate-500">Version</p>
        <p class="mt-2 font-mono text-lg font-bold text-indigo-600">{{ health?.version || '—' }}</p>
        <p class="mt-2 text-xs text-slate-500">Python Django + DRF Clean API</p>
      </div>
    </div>

    <div class="grid gap-4 md:grid-cols-3">
      <RouterLink
        to="/data-explorer"
        class="group rounded-xl border border-slate-200 bg-white p-5 shadow-xs transition hover:border-indigo-300"
      >
        <h3 class="text-base font-semibold text-slate-900 group-hover:text-indigo-600">
          Dynamic Data Explorer →
        </h3>
        <p class="mt-1 text-sm text-slate-500">
          Inspect Avro schemas and manage PostgreSQL &amp; MongoDB models with dynamic CRUD.
        </p>
      </RouterLink>

      <RouterLink
        to="/profile"
        class="group rounded-xl border border-slate-200 bg-white p-5 shadow-xs transition hover:border-indigo-300"
      >
        <h3 class="text-base font-semibold text-slate-900 group-hover:text-indigo-600">
          Profile &amp; JWT Session →
        </h3>
        <p class="mt-1 text-sm text-slate-500">
          Verify authenticated profile, test Refresh Token rotation, or revoke your session.
        </p>
      </RouterLink>

      <a
        :href="swaggerUrl"
        target="_blank"
        rel="noopener noreferrer"
        class="group rounded-xl border border-slate-200 bg-white p-5 shadow-xs transition hover:border-indigo-300"
      >
        <h3 class="text-base font-semibold text-slate-900 group-hover:text-indigo-600">
          Swagger UI ↗
        </h3>
        <p class="mt-1 text-sm text-slate-500">
          Open interactive OpenAPI documentation hosted by the backend server.
        </p>
      </a>
    </div>
  </div>
</template>
