<script setup lang="ts">
import { useToastStore } from '@/stores/toast.store'

const toastStore = useToastStore()

function variantClasses(variant: string): string {
  switch (variant) {
    case 'success':
      return 'border-emerald-200 bg-emerald-50 text-emerald-900'
    case 'error':
      return 'border-rose-200 bg-rose-50 text-rose-900'
    default:
      return 'border-sky-200 bg-sky-50 text-sky-900'
  }
}
</script>

<template>
  <div class="fixed right-4 top-4 z-50 flex w-80 flex-col gap-2">
    <div
      v-for="toast in toastStore.toasts"
      :key="toast.id"
      :class="['rounded-lg border px-4 py-3 shadow-md transition-all', variantClasses(toast.variant)]"
      role="status"
    >
      <div class="flex items-start justify-between gap-2">
        <div>
          <p class="text-sm font-semibold">{{ toast.title }}</p>
          <p v-if="toast.message" class="mt-0.5 text-xs opacity-90">{{ toast.message }}</p>
        </div>
        <button
          type="button"
          class="text-xs font-medium opacity-60 hover:opacity-100"
          @click="toastStore.remove(toast.id)"
        >
          ✕
        </button>
      </div>
    </div>
  </div>
</template>
