<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth.store'
import { useToastStore } from '@/stores/toast.store'
import { extractApiError, type ApiErrorResponse } from '@/types/api.types'

const EMAIL_PATTERN = /^[\w.-]+@([\w-]+\.)+[\w-]{2,4}$/

const router = useRouter()
const authStore = useAuthStore()
const toastStore = useToastStore()

const firstName = ref('')
const lastName = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const validationError = ref<string | null>(null)
const apiError = ref<ApiErrorResponse | null>(null)

async function handleSubmit(): Promise<void> {
  validationError.value = null
  apiError.value = null

  if (!firstName.value.trim() || !lastName.value.trim()) {
    validationError.value = 'First name and last name are required.'
    return
  }
  if (!EMAIL_PATTERN.test(email.value.trim())) {
    validationError.value = 'Please enter a valid email address.'
    return
  }
  if (password.value.length < 6) {
    validationError.value = 'Password must be at least 6 characters.'
    return
  }
  if (password.value !== confirmPassword.value) {
    validationError.value = 'Passwords do not match.'
    return
  }

  try {
    await authStore.register({
      first_name: firstName.value.trim(),
      last_name: lastName.value.trim(),
      email: email.value.trim(),
      password: password.value,
    })
    toastStore.success('Account created', 'You can now sign in with your credentials.')
    await router.push({ name: 'login' })
  } catch (err) {
    apiError.value = extractApiError(err)
  }
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center bg-slate-100 px-4">
    <div class="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
      <p class="text-xs font-semibold uppercase tracking-wider text-indigo-600">Clean Architecture</p>
      <h1 class="mt-1 text-2xl font-bold text-slate-900">Create account</h1>
      <p class="mt-1 text-sm text-slate-500">Register a new user via POST /api/v1/users/register.</p>

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
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-sm font-medium text-slate-700" for="reg-first">First name</label>
            <input
              id="reg-first"
              v-model="firstName"
              name="first_name"
              type="text"
              placeholder="Jane"
              class="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-700" for="reg-last">Last name</label>
            <input
              id="reg-last"
              v-model="lastName"
              name="last_name"
              type="text"
              placeholder="Doe"
              class="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
            />
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-700" for="reg-email">Email</label>
          <input
            id="reg-email"
            v-model="email"
            name="email"
            type="email"
            placeholder="jane@example.com"
            class="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-700" for="reg-password">Password</label>
          <input
            id="reg-password"
            v-model="password"
            name="password"
            type="password"
            autocomplete="new-password"
            placeholder="Minimum 6 characters"
            class="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-700" for="reg-confirm-password">
            Confirm password
          </label>
          <input
            id="reg-confirm-password"
            v-model="confirmPassword"
            name="confirm_password"
            type="password"
            autocomplete="new-password"
            placeholder="Re-enter your password"
            class="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
          />
        </div>

        <button
          type="submit"
          :disabled="authStore.loading"
          class="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {{ authStore.loading ? 'Creating account...' : 'Register' }}
        </button>
      </form>

      <p class="mt-6 text-center text-sm text-slate-500">
        Already have an account?
        <RouterLink to="/login" class="font-medium text-indigo-600 hover:text-indigo-500">
          Sign in
        </RouterLink>
      </p>
    </div>
  </div>
</template>
