<script setup lang="ts">
defineProps<{
  page: number
  pageSize: number
  totalPages: number
  totalData: number
}>()

const emit = defineEmits<{
  (e: 'update:page', value: number): void
  (e: 'update:pageSize', value: number): void
}>()

const pageSizeOptions = [10, 25, 50, 100]

function onPageSizeChange(event: Event): void {
  const target = event.target as HTMLSelectElement
  emit('update:pageSize', Number(target.value))
}
</script>

<template>
  <div class="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 px-4 py-3 text-sm text-slate-600">
    <div class="flex items-center gap-3">
      <span>
        Page <strong class="text-slate-900">{{ page }}</strong> of
        <strong class="text-slate-900">{{ totalPages }}</strong>
      </span>
      <span class="text-slate-300">|</span>
      <span>
        Total records: <strong class="text-slate-900">{{ totalData }}</strong>
      </span>
    </div>

    <div class="flex items-center gap-3">
      <label class="flex items-center gap-2 text-xs">
        <span>Rows</span>
        <select
          :value="pageSize"
          class="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700"
          @change="onPageSizeChange"
        >
          <option v-for="opt in pageSizeOptions" :key="opt" :value="opt">{{ opt }}</option>
        </select>
      </label>

      <div class="flex items-center gap-1">
        <button
          type="button"
          :disabled="page <= 1"
          class="rounded-md border border-slate-300 bg-white px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
          @click="emit('update:page', page - 1)"
        >
          Previous
        </button>
        <button
          type="button"
          :disabled="page >= totalPages"
          class="rounded-md border border-slate-300 bg-white px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
          @click="emit('update:page', page + 1)"
        >
          Next
        </button>
      </div>
    </div>
  </div>
</template>
