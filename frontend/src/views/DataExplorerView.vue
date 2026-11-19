<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useCrudStore } from '@/stores/crud.store'
import { useToastStore } from '@/stores/toast.store'
import AvroSchemaViewer from '@/components/crud/AvroSchemaViewer.vue'
import DynamicDataTable from '@/components/crud/DynamicDataTable.vue'
import DynamicFormModal from '@/components/crud/DynamicFormModal.vue'
import PaginationBar from '@/components/common/PaginationBar.vue'
import { extractApiError, type ApiErrorResponse } from '@/types/api.types'

const route = useRoute()
const crudStore = useCrudStore()
const toastStore = useToastStore()

const activeTab = ref<'records' | 'schema'>('records')
const apiError = ref<ApiErrorResponse | null>(null)
const detailOpen = ref(false)

const formOpen = ref(false)
const formMode = ref<'create' | 'edit'>('create')
const editingRow = ref<Record<string, unknown> | null>(null)
const formError = ref<ApiErrorResponse | null>(null)

const pendingDeleteId = ref<string | number | null>(null)

const activeSlug = computed(() => {
  const param = route.params.slug
  if (typeof param === 'string' && param.length > 0) {
    return param
  }
  return crudStore.models[0]?.slug ?? crudStore.selectedSlug
})

const activeModel = computed(() =>
  crudStore.models.find((model) => model.slug === activeSlug.value),
)

const allowedOps = computed(() => activeModel.value?.allowed_operations ?? ['read'])
const canCreate = computed(() => allowedOps.value.includes('create'))
const canUpdate = computed(() => allowedOps.value.includes('update'))
const canDelete = computed(() => allowedOps.value.includes('delete'))

function extractRowId(row: Record<string, unknown> | null): string | number | null {
  if (!row) return null
  const candidate = row.id ?? row.ID ?? row._id
  return typeof candidate === 'string' || typeof candidate === 'number' ? candidate : null
}

async function loadModel(slug: string): Promise<void> {
  if (!slug) return
  apiError.value = null
  detailOpen.value = false
  formOpen.value = false
  pendingDeleteId.value = null
  crudStore.clearDetail()
  try {
    await crudStore.selectModel(slug)
  } catch (err) {
    apiError.value = extractApiError(err)
  }
}

async function handlePageChange(nextPage: number): Promise<void> {
  apiError.value = null
  try {
    await crudStore.fetchList(activeSlug.value, nextPage, crudStore.pageSize)
  } catch (err) {
    apiError.value = extractApiError(err)
  }
}

async function handlePageSizeChange(nextSize: number): Promise<void> {
  apiError.value = null
  try {
    await crudStore.fetchList(activeSlug.value, 1, nextSize)
  } catch (err) {
    apiError.value = extractApiError(err)
  }
}

async function handleInspect(id: string | number): Promise<void> {
  apiError.value = null
  detailOpen.value = true
  try {
    await crudStore.fetchDetail(id)
  } catch (err) {
    apiError.value = extractApiError(err)
    detailOpen.value = false
  }
}

function closeDetail(): void {
  detailOpen.value = false
  crudStore.clearDetail()
}

function openCreateModal(): void {
  formMode.value = 'create'
  editingRow.value = null
  formError.value = null
  formOpen.value = true
}

function openEditModal(row: Record<string, unknown>): void {
  formMode.value = 'edit'
  editingRow.value = row
  formError.value = null
  formOpen.value = true
}

function closeFormModal(): void {
  formOpen.value = false
  editingRow.value = null
  formError.value = null
}

async function handleFormSubmit(payload: Record<string, unknown>): Promise<void> {
  formError.value = null
  try {
    if (formMode.value === 'create') {
      await crudStore.createItem(payload, activeSlug.value)
      toastStore.success('Record created', `Created new ${activeModel.value?.label || activeSlug.value} record.`)
    } else {
      const id = extractRowId(editingRow.value)
      if (id === null) return
      await crudStore.updateItem(id, payload, activeSlug.value)
      toastStore.success('Record updated', `Updated record #${id}.`)
    }
    closeFormModal()
  } catch (err) {
    formError.value = extractApiError(err)
  }
}

function openDeleteConfirm(id: string | number): void {
  pendingDeleteId.value = id
}

function cancelDelete(): void {
  pendingDeleteId.value = null
}

async function confirmDelete(): Promise<void> {
  if (pendingDeleteId.value === null) return
  const targetId = pendingDeleteId.value
  apiError.value = null
  try {
    await crudStore.deleteItem(targetId, activeSlug.value)
    toastStore.success('Record deleted', `Removed record #${targetId}.`)
    pendingDeleteId.value = null
  } catch (err) {
    apiError.value = extractApiError(err)
    pendingDeleteId.value = null
  }
}

onMounted(async () => {
  if (!crudStore.modelsLoaded) {
    try {
      await crudStore.fetchModels()
    } catch (err) {
      apiError.value = extractApiError(err)
    }
  }
})

watch(
  activeSlug,
  (slug) => {
    if (slug) {
      void loadModel(slug)
    }
  },
  { immediate: true },
)
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <div class="flex flex-wrap items-center gap-2.5">
          <h1 class="text-2xl font-bold text-slate-900">
            {{ activeModel?.label || activeSlug }}
          </h1>
          <span
            v-if="activeModel"
            :class="[
              'rounded-full px-2.5 py-0.5 font-mono text-xs font-medium uppercase',
              activeModel.datasource === 'mongodb'
                ? 'bg-emerald-100 text-emerald-700'
                : 'bg-indigo-100 text-indigo-700',
            ]"
          >
            {{ activeModel.datasource }}
          </span>
          <span
            v-if="activeModel"
            class="rounded-full bg-slate-200 px-2.5 py-0.5 text-xs font-medium text-slate-700"
          >
            {{ canCreate && canUpdate ? 'Full CRUD' : 'Audit · Read & Delete' }}
          </span>
        </div>
        <p class="mt-1 text-sm text-slate-500">
          Schema-driven table and form powered by Avro schema reflection
          <span class="font-mono text-xs text-slate-400">(/api/v1/data/{{ activeSlug }})</span>.
        </p>
      </div>

      <div class="flex items-center gap-2">
        <button
          v-if="canCreate"
          type="button"
          data-testid="create-record-btn"
          class="rounded-lg bg-indigo-600 px-3.5 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          @click="openCreateModal"
        >
          + Create
        </button>
        <button
          type="button"
          class="rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          @click="loadModel(activeSlug)"
        >
          Reload
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

    <!-- View tabs -->
    <div class="flex gap-2 border-b border-slate-200">
      <button
        type="button"
        :class="[
          '-mb-px border-b-2 px-4 py-2 text-sm font-medium',
          activeTab === 'records'
            ? 'border-indigo-600 text-indigo-600'
            : 'border-transparent text-slate-500 hover:text-slate-700',
        ]"
        @click="activeTab = 'records'"
      >
        Records ({{ crudStore.totalData }})
      </button>
      <button
        type="button"
        :class="[
          '-mb-px border-b-2 px-4 py-2 text-sm font-medium',
          activeTab === 'schema'
            ? 'border-indigo-600 text-indigo-600'
            : 'border-transparent text-slate-500 hover:text-slate-700',
        ]"
        @click="activeTab = 'schema'"
      >
        Avro Schema
      </button>
    </div>

    <!-- Records Table -->
    <div v-if="activeTab === 'records'" class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs">
      <DynamicDataTable
        :schema="crudStore.schema"
        :items="crudStore.items"
        :loading="crudStore.loadingList"
        :can-update="canUpdate"
        :can-delete="canDelete"
        @inspect="handleInspect"
        @edit="openEditModal"
        @delete="openDeleteConfirm"
      />
      <PaginationBar
        :page="crudStore.page"
        :page-size="crudStore.pageSize"
        :total-pages="crudStore.totalPages"
        :total-data="crudStore.totalData"
        @update:page="handlePageChange"
        @update:page-size="handlePageSizeChange"
      />
    </div>

    <!-- Avro Schema Viewer -->
    <AvroSchemaViewer
      v-else
      :schema="crudStore.schema"
      :loading="crudStore.loadingSchema"
    />

    <!-- Detail Modal -->
    <div
      v-if="detailOpen"
      class="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/40 p-4"
      @click.self="closeDetail"
    >
      <div class="w-full max-w-xl rounded-2xl bg-white p-6 shadow-xl">
        <div class="flex items-center justify-between border-b border-slate-200 pb-3">
          <div>
            <h3 class="text-base font-semibold text-slate-900">Record Detail</h3>
            <p class="font-mono text-xs text-slate-500">/api/v1/data/{{ crudStore.selectedSlug }}</p>
          </div>
          <button
            type="button"
            class="rounded-md px-2 py-1 text-sm text-slate-500 hover:bg-slate-100"
            @click="closeDetail"
          >
            ✕
          </button>
        </div>

        <div v-if="crudStore.loadingDetail" class="py-8 text-center text-sm text-slate-500">
          Loading record...
        </div>

        <pre
          v-else-if="crudStore.selectedItem"
          class="mt-4 max-h-96 overflow-auto rounded-lg bg-slate-900 p-4 text-xs text-slate-100"
        >{{ JSON.stringify(crudStore.selectedItem, null, 2) }}</pre>

        <div class="mt-4 flex justify-end">
          <button
            type="button"
            class="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            @click="closeDetail"
          >
            Close
          </button>
        </div>
      </div>
    </div>

    <!-- Dynamic Create / Edit Form Modal -->
    <DynamicFormModal
      :open="formOpen"
      :mode="formMode"
      :schema="crudStore.schema"
      :initial-data="editingRow"
      :entity-label="activeModel?.label || activeSlug"
      :submitting="crudStore.submitting"
      :error="formError"
      @close="closeFormModal"
      @submit="handleFormSubmit"
    />

    <!-- Delete Confirmation Modal -->
    <div
      v-if="pendingDeleteId !== null"
      data-testid="delete-confirm-modal"
      class="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/40 p-4"
      @click.self="cancelDelete"
    >
      <div class="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        <h3 class="text-base font-semibold text-slate-900">Delete Record</h3>
        <p class="mt-2 text-sm text-slate-600">
          Are you sure you want to permanently delete record
          <span class="font-mono font-semibold text-slate-900">#{{ pendingDeleteId }}</span>
          from <span class="font-mono">{{ activeSlug }}</span>?
        </p>
        <div class="mt-5 flex justify-end gap-2">
          <button
            type="button"
            class="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            @click="cancelDelete"
          >
            Cancel
          </button>
          <button
            type="button"
            data-testid="confirm-delete-btn"
            :disabled="crudStore.submitting"
            class="rounded-lg bg-rose-600 px-4 py-2 text-sm font-medium text-white hover:bg-rose-700 disabled:opacity-50"
            @click="confirmDelete"
          >
            {{ crudStore.submitting ? 'Deleting...' : 'Delete' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
