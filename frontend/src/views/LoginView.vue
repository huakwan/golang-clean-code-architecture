<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth.store'
import { useToastStore } from '@/stores/toast.store'
import { extractApiError, type ApiErrorResponse } from '@/types/api.types'

const EMAIL_PATTERN = /^[\w.-]+@([\w-]+\.)+[\w-]{2,4}$/

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const toastStore = useToastStore()

const email = ref('')
const password = ref('')
const validationError = ref<string | null>(null)
const apiError = ref<ApiErrorResponse | null>(null)

async function handleSubmit(): Promise<void> {
  validationError.value = null
  apiError.value = null

  if (!EMAIL_PATTERN.test(email.value.trim())) {
    validationError.value = 'Please enter a valid email address.'
    return
  }
  if (!password.value) {
    validationError.value = 'Password is required.'
    return
  }

  try {
    await authStore.login({ email: email.value.trim(), password: password.value })
    toastStore.success('Welcome back', 'Signed in successfully.')
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    await router.push(redirect)
  } catch (err) {
    apiError.value = extractApiError(err)
  }
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center bg-slate-100 px-4">
    <div class="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
      <p class="text-xs font-semibold uppercase tracking-wider text-indigo-600">Clean Architecture</p>
      <h1 class="mt-1 text-2xl font-bold text-slate-900">Sign in</h1>
      <p class="mt-1 text-sm text-slate-500">Authenticate with your account to access the console.</p>

      <div
        v-if="validationError"
        class="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800"
      >
        {{ validationError }}
      </div>

      <div
        v-if="apiError"
        class="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"
      >
        <p class="font-mono text-xs font-semibold">{{ apiError.trace_id }}</p>
        <p class="mt-0.5">{{ apiError.message }}</p>
      </div>

      <form class="mt-6 space-y-4" novalidate @submit.prevent="handleSubmit">
        <div>
          <label class="block text-sm font-medium text-slate-700" for="login-email">Email</label>
          <input
            id="login-email"
            v-model="email"
            name="email"
            type="email"
            autocomplete="email"
            placeholder="you@example.com"
            class="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-700" for="login-password">Password</label>
          <input
            id="login-password"
            v-model="password"
            name="password"
            type="password"
            autocomplete="current-password"
            placeholder="••••••••"
            class="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
          />
        </div>

        <button
          type="submit"
          :disabled="authStore.loading"
          class="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {{ authStore.loading ? 'Signing in...' : 'Sign in' }}
        </button>
      </form>

      <p class="mt-6 text-center text-sm text-slate-500">
        Don't have an account?
        <RouterLink to="/register" class="font-medium text-indigo-600 hover:text-indigo-500">
          Create one
        </RouterLink>
      </p>
    </div>
  </div>
</template>
