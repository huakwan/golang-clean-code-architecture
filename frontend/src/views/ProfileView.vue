<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAuthStore } from '@/stores/auth.store'
import { useToastStore } from '@/stores/toast.store'
import { extractApiError, type ApiErrorResponse } from '@/types/api.types'

const authStore = useAuthStore()
const toastStore = useToastStore()

const apiError = ref<ApiErrorResponse | null>(null)
const showTokens = ref(false)

async function loadProfile(): Promise<void> {
  apiError.value = null
  try {
    await authStore.fetchProfile()
  } catch (err) {
    apiError.value = extractApiError(err)
  }
}

async function handleRefreshToken(): Promise<void> {
  apiError.value = null
  try {
    await authStore.refresh()
    toastStore.success('Token refreshed', 'A new access token was issued.')
  } catch (err) {
    apiError.value = extractApiError(err)
    toastStore.error('Refresh failed', apiError.value.message)
  }
}

function maskToken(token: string | null): string {
  if (!token) return '—'
  if (showTokens.value) return token
  return `${token.slice(0, 18)}••••••••••••••••${token.slice(-10)}`
}

onMounted(() => {
  void loadProfile()
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Profile &amp; Auth Session</h1>
        <p class="mt-1 text-sm text-slate-500">
          Authenticated user profile and JWT token lifecycle controls.
        </p>
      </div>
      <div class="flex items-center gap-2">
        <button
          type="button"
          :disabled="authStore.loading"
          class="rounded-lg bg-indigo-600 px-3.5 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          @click="handleRefreshToken"
        >
          Test Refresh Token
        </button>
      </div>
    </div>

    <div
      v-if="apiError"
      class="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"
    >
      <span class="font-mono text-xs font-semibold">{{ apiError.trace_id }}</span>:
      {{ apiError.message }}
    </div>

    <div class="grid gap-6 lg:grid-cols-2">
      <!-- User Info -->
      <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
        <h2 class="text-base font-semibold text-slate-900">User Identity</h2>
        <dl v-if="authStore.user" class="mt-4 divide-y divide-slate-100 text-sm">
          <div class="flex justify-between py-2.5">
            <dt class="text-slate-500">User ID</dt>
            <dd class="font-mono font-medium text-slate-900">{{ authStore.user.id }}</dd>
          </div>
          <div class="flex justify-between py-2.5">
            <dt class="text-slate-500">Email</dt>
            <dd class="font-medium text-slate-900">{{ authStore.user.email }}</dd>
          </div>
          <div class="flex justify-between py-2.5">
            <dt class="text-slate-500">First Name</dt>
            <dd class="text-slate-900">{{ authStore.user.first_name }}</dd>
          </div>
          <div class="flex justify-between py-2.5">
            <dt class="text-slate-500">Last Name</dt>
            <dd class="text-slate-900">{{ authStore.user.last_name }}</dd>
          </div>
          <div class="flex justify-between py-2.5">
            <dt class="text-slate-500">Created At</dt>
            <dd class="font-mono text-xs text-slate-700">{{ authStore.user.created_at }}</dd>
          </div>
          <div class="flex justify-between py-2.5">
            <dt class="text-slate-500">Updated At</dt>
            <dd class="font-mono text-xs text-slate-700">{{ authStore.user.updated_at }}</dd>
          </div>
        </dl>
        <p v-else class="mt-4 text-sm text-slate-500">No profile loaded yet.</p>
      </div>

      <!-- Token Inspector -->
      <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
        <div class="flex items-center justify-between">
          <h2 class="text-base font-semibold text-slate-900">JWT Token Inspector</h2>
          <button
            type="button"
            class="text-xs font-medium text-indigo-600 hover:text-indigo-500"
            @click="showTokens = !showTokens"
          >
            {{ showTokens ? 'Hide tokens' : 'Reveal tokens' }}
          </button>
        </div>

        <div class="mt-4 space-y-4">
          <div>
            <p class="text-xs font-semibold uppercase tracking-wider text-slate-500">Access Token</p>
            <p class="mt-1 break-all rounded-lg bg-slate-50 p-3 font-mono text-xs text-slate-700">
              {{ maskToken(authStore.accessToken) }}
            </p>
          </div>
          <div>
            <p class="text-xs font-semibold uppercase tracking-wider text-slate-500">Refresh Token</p>
            <p class="mt-1 break-all rounded-lg bg-slate-50 p-3 font-mono text-xs text-slate-700">
              {{ maskToken(authStore.refreshToken) }}
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
