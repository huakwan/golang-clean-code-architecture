import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import { createRouter, createMemoryHistory } from 'vue-router'
import DataExplorerView from '@/views/DataExplorerView.vue'
import { useCrudStore } from '@/stores/crud.store'
import type { EntityModelOption } from '@/types/crud.types'

const SAMPLE_MODELS: EntityModelOption[] = [
  {
    slug: 'users',
    label: 'Users',
    datasource: 'postgresql',
    allowed_operations: ['read', 'create', 'update', 'delete'],
  },
  {
    slug: 'user-tokens',
    label: 'User Tokens',
    datasource: 'postgresql',
    allowed_operations: ['read', 'create', 'update', 'delete'],
  },
  {
    slug: 'activity-logs',
    label: 'Activity Logs',
    datasource: 'mongodb',
    allowed_operations: ['read', 'delete'],
  },
]

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: '/data-explorer/:slug?',
        name: 'data-explorer',
        component: DataExplorerView,
      },
    ],
  })
}

describe('DataExplorerView', () => {
  it('loads the model from the route slug and reloads when the route slug changes', async () => {
    const router = makeRouter()
    await router.push('/data-explorer/user-tokens')
    await router.isReady()

    const pinia = createTestingPinia({
      createSpy: vi.fn,
      initialState: {
        crud: {
          models: SAMPLE_MODELS,
          modelsLoaded: true,
          selectedSlug: 'user-tokens',
        },
      },
    })
    const crudStore = useCrudStore(pinia)
    vi.mocked(crudStore.selectModel).mockResolvedValue(undefined)

    const wrapper = mount(DataExplorerView, {
      global: { plugins: [pinia, router] },
    })
    await flushPromises()

    expect(crudStore.selectModel).toHaveBeenCalledWith('user-tokens')
    expect(wrapper.text()).toContain('User Tokens')
    expect(wrapper.find('[data-testid="create-record-btn"]').exists()).toBe(true)

    await router.push('/data-explorer/activity-logs')
    await flushPromises()

    expect(crudStore.selectModel).toHaveBeenCalledWith('activity-logs')
  })

  it('falls back to the first registered model when no slug param is provided', async () => {
    const router = makeRouter()
    await router.push('/data-explorer')
    await router.isReady()

    const pinia = createTestingPinia({
      createSpy: vi.fn,
      initialState: {
        crud: {
          models: SAMPLE_MODELS,
          modelsLoaded: true,
          selectedSlug: 'users',
        },
      },
    })
    const crudStore = useCrudStore(pinia)
    vi.mocked(crudStore.selectModel).mockResolvedValue(undefined)

    mount(DataExplorerView, {
      global: { plugins: [pinia, router] },
    })
    await flushPromises()

    expect(crudStore.selectModel).toHaveBeenCalledWith('users')
  })

  it('hides Create and Edit buttons for activity-logs while keeping View and Delete', async () => {
    const router = makeRouter()
    await router.push('/data-explorer/activity-logs')
    await router.isReady()

    const pinia = createTestingPinia({
      createSpy: vi.fn,
      initialState: {
        crud: {
          models: SAMPLE_MODELS,
          modelsLoaded: true,
          selectedSlug: 'activity-logs',
          schema: {
            type: 'record',
            name: 'activity-logs',
            fields: [
              { name: 'id', type: 'string' },
              { name: 'action', type: 'string' },
            ],
          },
          items: [{ id: 'abc123', action: 'USER_LOGIN' }],
          totalData: 1,
        },
      },
    })
    const crudStore = useCrudStore(pinia)
    vi.mocked(crudStore.selectModel).mockResolvedValue(undefined)
    vi.mocked(crudStore.deleteItem).mockResolvedValue(undefined)

    const wrapper = mount(DataExplorerView, {
      global: { plugins: [pinia, router] },
    })
    await flushPromises()

    expect(wrapper.find('[data-testid="create-record-btn"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="edit-row"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="inspect-row"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="delete-row"]').exists()).toBe(true)

    await wrapper.find('[data-testid="delete-row"]').trigger('click')
    expect(wrapper.find('[data-testid="delete-confirm-modal"]').exists()).toBe(true)

    await wrapper.find('[data-testid="confirm-delete-btn"]').trigger('click')
    await flushPromises()
    expect(crudStore.deleteItem).toHaveBeenCalledWith('abc123', 'activity-logs')
  })
})
