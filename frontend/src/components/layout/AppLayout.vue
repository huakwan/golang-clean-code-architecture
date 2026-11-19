<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth.store'
import { useCrudStore } from '@/stores/crud.store'
import { useToastStore } from '@/stores/toast.store'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const crudStore = useCrudStore()
const toastStore = useToastStore()

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const appTitle = import.meta.env.VITE_APP_TITLE || 'Clean Architecture Console'

const dataExplorerOpen = ref(true)

const isDataExplorerRoute = computed(() => route.name === 'data-explorer')

const activeExplorerSlug = computed(() => {
  const param = route.params.slug
  if (typeof param === 'string' && param.length > 0) {
    return param
  }
  return crudStore.selectedSlug || crudStore.models[0]?.slug || ''
})

watch(isDataExplorerRoute, (isActive) => {
  if (isActive) {
    dataExplorerOpen.value = true
  }
})

onMounted(() => {
  if (!crudStore.modelsLoaded) {
    void crudStore.fetchModels().catch(() => {})
  }
})

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
    <aside class="sticky top-0 flex h-screen w-64 shrink-0 flex-col border-r border-slate-200 bg-slate-900 text-slate-100">
      <div class="border-b border-slate-800 px-5 py-4">
        <p class="text-xs font-semibold uppercase tracking-wider text-indigo-400">Clean Arch</p>
        <h1 class="mt-0.5 text-base font-bold text-white">{{ appTitle }}</h1>
      </div>

      <nav class="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        <RouterLink
          to="/"
          :class="[
            'block rounded-lg px-3 py-2 text-sm font-medium transition-colors',
            route.name === 'dashboard'
              ? 'bg-indigo-600 text-white'
              : 'text-slate-300 hover:bg-slate-800 hover:text-white',
          ]"
        >
          Dashboard
        </RouterLink>

        <!-- Data Explorer collapsible submenu -->
        <div>
          <button
            type="button"
            data-testid="data-explorer-toggle"
            :aria-expanded="dataExplorerOpen"
            :class="[
              'flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm font-medium transition-colors',
              isDataExplorerRoute
                ? 'bg-slate-800 text-white'
                : 'text-slate-300 hover:bg-slate-800 hover:text-white',
            ]"
            @click="dataExplorerOpen = !dataExplorerOpen"
          >
            <span>Data Explorer</span>
            <span
              :class="[
                'text-xs text-slate-400 transition-transform',
                dataExplorerOpen ? 'rotate-90' : '',
              ]"
            >
              ▸
            </span>
          </button>

          <div
            v-if="dataExplorerOpen"
            class="mt-1 space-y-0.5 border-l border-slate-800 pl-3 ml-3"
          >
            <RouterLink
              v-for="model in crudStore.models"
              :key="model.slug"
              data-testid="data-explorer-submenu-item"
              :to="{ name: 'data-explorer', params: { slug: model.slug } }"
              :class="[
                'flex items-center justify-between gap-2 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors',
                isDataExplorerRoute && activeExplorerSlug === model.slug
                  ? 'bg-indigo-600 text-white'
                  : 'text-slate-400 hover:bg-slate-800 hover:text-white',
              ]"
            >
              <span class="truncate">{{ model.label }}</span>
              <span
                :class="[
                  'shrink-0 rounded px-1.5 py-0.5 font-mono text-[9px] uppercase',
                  isDataExplorerRoute && activeExplorerSlug === model.slug
                    ? 'bg-indigo-500 text-white'
                    : model.datasource === 'mongodb'
                      ? 'bg-emerald-900/60 text-emerald-300'
                      : 'bg-slate-800 text-slate-400',
                ]"
              >
                {{ model.datasource }}
              </span>
            </RouterLink>
          </div>
        </div>

        <RouterLink
          to="/profile"
          :class="[
            'block rounded-lg px-3 py-2 text-sm font-medium transition-colors',
            route.name === 'profile'
              ? 'bg-indigo-600 text-white'
              : 'text-slate-300 hover:bg-slate-800 hover:text-white',
          ]"
        >
          Profile &amp; Auth
        </RouterLink>
      </nav>

      <div class="border-t border-slate-800 px-4 py-3 text-xs text-slate-400">
        <p class="font-medium text-slate-300">API Target</p>
        <p class="mt-0.5 truncate font-mono text-[11px] text-indigo-300">{{ apiBaseUrl }}</p>
      </div>
    </aside>

    <!-- Main area -->
    <div class="flex min-w-0 flex-1 flex-col">
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

      <main class="min-w-0 flex-1 p-6">
        <slot />
      </main>
    </div>
  </div>
</template>
