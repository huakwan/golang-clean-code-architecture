<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth.store'
import { useToastStore } from '@/stores/toast.store'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const toastStore = useToastStore()

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000'
const appTitle = import.meta.env.VITE_APP_TITLE || 'Clean Architecture Console'

const navItems = [
  { to: '/', name: 'dashboard', label: 'Dashboard' },
  { to: '/data-explorer', name: 'data-explorer', label: 'Data Explorer' },
  { to: '/profile', name: 'profile', label: 'Profile & Auth' },
]

const displayName = computed(() => {
  if (!authStore.user) return 'Authenticated User'
  const full = `${authStore.user.first_name} ${authStore.user.last_name}`.trim()
  return full || authStore.user.email
})

async function handleLogout(): Promise<void> {
  await authStore.logout()
  toastStore.info('Signed out', 'Your session has been cleared.')
  await router.push({ name: 'login' })
}
</script>

<template>
  <div class="flex min-h-screen bg-slate-50">
    <!-- Sidebar -->
    <aside class="flex w-64 flex-col border-r border-slate-200 bg-slate-900 text-slate-100">
      <div class="border-b border-slate-800 px-5 py-4">
        <p class="text-xs font-semibold uppercase tracking-wider text-indigo-400">Clean Arch</p>
        <h1 class="mt-0.5 text-base font-bold text-white">{{ appTitle }}</h1>
      </div>

      <nav class="flex-1 space-y-1 px-3 py-4">
        <RouterLink
          v-for="item in navItems"
          :key="item.name"
          :to="item.to"
          :class="[
            'block rounded-lg px-3 py-2 text-sm font-medium transition-colors',
            route.name === item.name
              ? 'bg-indigo-600 text-white'
              : 'text-slate-300 hover:bg-slate-800 hover:text-white',
          ]"
        >
          {{ item.label }}
        </RouterLink>
      </nav>

      <div class="border-t border-slate-800 px-4 py-3 text-xs text-slate-400">
        <p class="font-medium text-slate-300">API Target</p>
        <p class="mt-0.5 truncate font-mono text-[11px] text-indigo-300">{{ apiBaseUrl }}</p>
      </div>
    </aside>

    <!-- Main area -->
    <div class="flex flex-1 flex-col">
      <header class="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3.5">
        <h2 class="text-sm font-semibold text-slate-700">
          {{ route.meta.title || 'Workspace' }}
        </h2>

        <div class="flex items-center gap-4">
          <div class="text-right">
            <p class="text-sm font-medium text-slate-900">{{ displayName }}</p>
            <p v-if="authStore.user?.email" class="text-xs text-slate-500">
              {{ authStore.user.email }}
            </p>
          </div>
          <button
            type="button"
            class="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100"
            @click="handleLogout"
          >
            Logout
          </button>
        </div>
      </header>

      <main class="flex-1 p-6">
        <slot />
      </main>
    </div>
  </div>
</template>
