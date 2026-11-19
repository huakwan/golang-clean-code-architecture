import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import { createRouter, createMemoryHistory } from 'vue-router'
import AppLayout from '@/components/layout/AppLayout.vue'

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'dashboard', meta: { title: 'Dashboard' }, component: { template: '<div />' } },
      {
        path: '/data-explorer/:slug?',
        name: 'data-explorer',
        meta: { title: 'Data Explorer' },
        component: { template: '<div />' },
      },
      { path: '/profile', name: 'profile', meta: { title: 'Profile' }, component: { template: '<div />' } },
      { path: '/login', name: 'login', component: { template: '<div />' } },
    ],
  })
}

describe('AppLayout', () => {
  it('keeps sidebar at a fixed non-shrinking width and constrains main area against wide content', async () => {
    const router = makeRouter()
    await router.push('/data-explorer')
    await router.isReady()

    const wrapper = mount(AppLayout, {
      global: {
        plugins: [createTestingPinia({ createSpy: vi.fn }), router],
      },
      slots: {
        default: '<div class="w-[2000px]">Wide table content</div>',
      },
    })

    const sidebar = wrapper.find('aside')
    expect(sidebar.exists()).toBe(true)
    expect(sidebar.classes()).toContain('w-64')
    expect(sidebar.classes()).toContain('shrink-0')

    const main = wrapper.find('main')
    expect(main.exists()).toBe(true)
    const mainColumn = main.element.parentElement
    expect(mainColumn?.classList.contains('flex-1')).toBe(true)
    expect(mainColumn?.classList.contains('min-w-0')).toBe(true)
  })

  it('renders Data Explorer models as sidebar submenu links and highlights the active slug', async () => {
    const router = makeRouter()
    await router.push('/data-explorer/user-tokens')
    await router.isReady()

    const wrapper = mount(AppLayout, {
      global: {
        plugins: [createTestingPinia({ createSpy: vi.fn }), router],
      },
    })

    const submenuLinks = wrapper.findAll('[data-testid="data-explorer-submenu-item"]')
    expect(submenuLinks).toHaveLength(3)
    expect(submenuLinks.map((link) => link.attributes('href'))).toEqual([
      '/data-explorer/users',
      '/data-explorer/user-tokens',
      '/data-explorer/user-permissions',
    ])

    const activeLink = submenuLinks.find((link) => link.attributes('href') === '/data-explorer/user-tokens')
    expect(activeLink?.classes()).toContain('bg-indigo-600')

    const inactiveLink = submenuLinks.find((link) => link.attributes('href') === '/data-explorer/users')
    expect(inactiveLink?.classes()).not.toContain('bg-indigo-600')
  })

  it('toggles the Data Explorer submenu when clicking the parent button', async () => {
    const router = makeRouter()
    await router.push('/')
    await router.isReady()

    const wrapper = mount(AppLayout, {
      global: {
        plugins: [createTestingPinia({ createSpy: vi.fn }), router],
      },
    })

    const toggleBtn = wrapper.find('[data-testid="data-explorer-toggle"]')
    expect(toggleBtn.exists()).toBe(true)
    expect(wrapper.findAll('[data-testid="data-explorer-submenu-item"]')).toHaveLength(3)

    await toggleBtn.trigger('click')
    expect(wrapper.findAll('[data-testid="data-explorer-submenu-item"]')).toHaveLength(0)

    await toggleBtn.trigger('click')
    expect(wrapper.findAll('[data-testid="data-explorer-submenu-item"]')).toHaveLength(3)
  })
})
