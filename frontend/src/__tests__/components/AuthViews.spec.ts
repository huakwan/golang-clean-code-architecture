import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import { createRouter, createMemoryHistory } from 'vue-router'
import axios from 'axios'
import LoginView from '@/views/LoginView.vue'
import RegisterView from '@/views/RegisterView.vue'
import { useAuthStore } from '@/stores/auth.store'

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/login', name: 'login', component: LoginView },
      { path: '/register', name: 'register', component: RegisterView },
      { path: '/', name: 'dashboard', component: { template: '<div>Dashboard</div>' } },
    ],
  })
}

describe('AuthViews (LoginView & RegisterView)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows client-side validation error on empty Login submit', async () => {
    const router = makeRouter()
    const wrapper = mount(LoginView, {
      global: {
        plugins: [createTestingPinia({ createSpy: vi.fn }), router],
      },
    })

    await wrapper.find('form').trigger('submit.prevent')
    expect(wrapper.text()).toContain('Please enter a valid email address')
  })

  it('displays backend trace_id and message on Login failure', async () => {
    const router = makeRouter()
    const pinia = createTestingPinia({ createSpy: vi.fn })
    const authStore = useAuthStore(pinia)

    const apiErr = new axios.AxiosError('Bad Request', 'ERR_BAD_REQUEST', undefined, null, {
      data: { trace_id: 'users-002', message: 'invalid credentials' },
      status: 400,
      statusText: 'Bad Request',
      headers: {},
      config: {} as never,
    })
    vi.mocked(authStore.login).mockRejectedValueOnce(apiErr)

    const wrapper = mount(LoginView, {
      global: { plugins: [pinia, router] },
    })

    await wrapper.find('input[type="email"]').setValue('user@example.com')
    await wrapper.find('input[type="password"]').setValue('wrongpass')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(wrapper.text()).toContain('users-002')
    expect(wrapper.text()).toContain('invalid credentials')
  })

  it('validates email pattern on RegisterView before calling API', async () => {
    const router = makeRouter()
    const pinia = createTestingPinia({ createSpy: vi.fn })
    const authStore = useAuthStore(pinia)

    const wrapper = mount(RegisterView, {
      global: { plugins: [pinia, router] },
    })

    await wrapper.find('input[name="first_name"]').setValue('Jane')
    await wrapper.find('input[name="last_name"]').setValue('Doe')
    await wrapper.find('input[name="email"]').setValue('not-an-email')
    await wrapper.find('input[name="password"]').setValue('secret123')
    await wrapper.find('form').trigger('submit.prevent')

    expect(wrapper.text()).toContain('Please enter a valid email address')
    expect(authStore.register).not.toHaveBeenCalled()
  })

  it('shows validation error when confirm password does not match password on RegisterView', async () => {
    const router = makeRouter()
    const pinia = createTestingPinia({ createSpy: vi.fn })
    const authStore = useAuthStore(pinia)

    const wrapper = mount(RegisterView, {
      global: { plugins: [pinia, router] },
    })

    await wrapper.find('input[name="first_name"]').setValue('Jane')
    await wrapper.find('input[name="last_name"]').setValue('Doe')
    await wrapper.find('input[name="email"]').setValue('jane@example.com')
    await wrapper.find('input[name="password"]').setValue('secret123')
    await wrapper.find('input[name="confirm_password"]').setValue('different123')
    await wrapper.find('form').trigger('submit.prevent')

    expect(wrapper.text()).toContain('Passwords do not match.')
    expect(authStore.register).not.toHaveBeenCalled()
  })

  it('submits registration when confirm password matches password', async () => {
    const router = makeRouter()
    const pinia = createTestingPinia({ createSpy: vi.fn })
    const authStore = useAuthStore(pinia)
    vi.mocked(authStore.register).mockResolvedValueOnce({
      id: 1,
      email: 'jane@example.com',
      first_name: 'Jane',
      last_name: 'Doe',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    })

    const wrapper = mount(RegisterView, {
      global: { plugins: [pinia, router] },
    })

    await wrapper.find('input[name="first_name"]').setValue('Jane')
    await wrapper.find('input[name="last_name"]').setValue('Doe')
    await wrapper.find('input[name="email"]').setValue('jane@example.com')
    await wrapper.find('input[name="password"]').setValue('secret123')
    await wrapper.find('input[name="confirm_password"]').setValue('secret123')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(authStore.register).toHaveBeenCalledWith({
      first_name: 'Jane',
      last_name: 'Doe',
      email: 'jane@example.com',
      password: 'secret123',
    })
  })
})
