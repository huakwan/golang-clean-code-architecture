import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import { createRouter, createMemoryHistory } from 'vue-router'
import DataExplorerView from '@/views/DataExplorerView.vue'
import { useCrudStore } from '@/stores/crud.store'

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

    const pinia = createTestingPinia({ createSpy: vi.fn })
    const crudStore = useCrudStore(pinia)
    vi.mocked(crudStore.selectModel).mockResolvedValue(undefined)

    const wrapper = mount(DataExplorerView, {
      global: { plugins: [pinia, router] },
    })
    await flushPromises()

    expect(crudStore.selectModel).toHaveBeenCalledWith('user-tokens')
    expect(wrapper.text()).toContain('User Tokens')
    expect(wrapper.find('[data-testid="model-selector"]').exists()).toBe(false)

    await router.push('/data-explorer/user-permissions')
    await flushPromises()

    expect(crudStore.selectModel).toHaveBeenCalledWith('user-permissions')
  })

  it('falls back to the first registered model when no slug param is provided', async () => {
    const router = makeRouter()
    await router.push('/data-explorer')
    await router.isReady()

    const pinia = createTestingPinia({ createSpy: vi.fn })
    const crudStore = useCrudStore(pinia)
    vi.mocked(crudStore.selectModel).mockResolvedValue(undefined)

    mount(DataExplorerView, {
      global: { plugins: [pinia, router] },
    })
    await flushPromises()

    expect(crudStore.selectModel).toHaveBeenCalledWith('users')
  })
})
