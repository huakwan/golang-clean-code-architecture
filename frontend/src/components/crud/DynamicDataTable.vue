<script setup lang="ts">
import { computed } from 'vue'
import type { AvroSchema } from '@/types/crud.types'

const props = defineProps<{
  schema: AvroSchema | null
  items: Record<string, unknown>[]
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'inspect', id: string | number): void
}>()

const columns = computed<string[]>(() => {
  const fromSchema = (props.schema?.fields ?? [])
    .map((field) => field.name)
    .filter((name): name is string => Boolean(name && name !== 'password'))

  if (props.items.length > 0) {
    const fromData = Object.keys(props.items[0]).filter((key) => key !== 'password')
    if (fromSchema.length === 0) {
      return fromData
    }
    const merged = [...fromSchema]
    for (const key of fromData) {
      if (!merged.includes(key)) {
        merged.push(key)
      }
    }
    return merged
  }

  return fromSchema
})

function extractRowId(row: Record<string, unknown>): string | number | null {
  const candidate = row.id ?? row.ID ?? row._id
  if (typeof candidate === 'string' || typeof candidate === 'number') {
    return candidate
  }
  return null
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'object') return JSON.stringify(value)
  const text = String(value)
  return text.length > 48 ? `${text.slice(0, 48)}…` : text
}
</script>

<template>
  <div class="overflow-x-auto">
    <div v-if="loading" class="p-8 text-center text-sm text-slate-500">Loading records...</div>

    <div v-else-if="items.length === 0" class="p-8 text-center text-sm text-slate-500">
      No records found.
    </div>

    <table v-else class="min-w-full divide-y divide-slate-200 text-left text-sm">
      <thead class="bg-slate-50">
        <tr>
          <th
            v-for="col in columns"
            :key="col"
            class="whitespace-nowrap px-4 py-3 font-mono text-xs font-semibold uppercase tracking-wider text-slate-600"
          >
            {{ col }}
          </th>
          <th class="whitespace-nowrap px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-600">
            Actions
          </th>
        </tr>
      </thead>
      <tbody class="divide-y divide-slate-100 bg-white">
        <tr v-for="(row, rowIdx) in items" :key="extractRowId(row) ?? rowIdx" class="hover:bg-slate-50">
          <td
            v-for="col in columns"
            :key="col"
            class="max-w-xs truncate whitespace-nowrap px-4 py-3 font-mono text-xs text-slate-700"
          >
            {{ formatCell(row[col]) }}
          </td>
          <td class="whitespace-nowrap px-4 py-3 text-right">
            <button
              v-if="extractRowId(row) !== null"
              type="button"
              data-testid="inspect-row"
              class="rounded-md border border-indigo-200 bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-100"
              @click="emit('inspect', extractRowId(row)!)"
            >
              View
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
