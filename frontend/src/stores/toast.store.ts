import { ref } from 'vue'
import { defineStore } from 'pinia'

export type ToastVariant = 'success' | 'error' | 'info'

export interface ToastItem {
  id: number
  variant: ToastVariant
  title: string
  message?: string
}

export const useToastStore = defineStore('toast', () => {
  const toasts = ref<ToastItem[]>([])
  let nextId = 1

  function push(variant: ToastVariant, title: string, message?: string, durationMs = 4000): void {
    const id = nextId++
    toasts.value.push({ id, variant, title, message })
    if (durationMs > 0) {
      setTimeout(() => remove(id), durationMs)
    }
  }

  function remove(id: number): void {
    toasts.value = toasts.value.filter((item) => item.id !== id)
  }

  return {
    toasts,
    push,
    remove,
    success: (title: string, message?: string) => push('success', title, message),
    error: (title: string, message?: string) => push('error', title, message, 6000),
    info: (title: string, message?: string) => push('info', title, message),
  }
})
