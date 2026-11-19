import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth.store'
import LoginView from '@/views/LoginView.vue'
import RegisterView from '@/views/RegisterView.vue'
import DashboardView from '@/views/DashboardView.vue'
import ProfileView from '@/views/ProfileView.vue'
import DataExplorerView from '@/views/DataExplorerView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { guestOnly: true, title: 'Sign in' },
    },
    {
      path: '/register',
      name: 'register',
      component: RegisterView,
      meta: { guestOnly: true, title: 'Register' },
    },
    {
      path: '/',
      name: 'dashboard',
      component: DashboardView,
      meta: { requiresAuth: true, title: 'Dashboard' },
    },
    {
      path: '/profile',
      name: 'profile',
      component: ProfileView,
      meta: { requiresAuth: true, title: 'Profile & Auth' },
    },
    {
      path: '/data-explorer',
      name: 'data-explorer',
      component: DataExplorerView,
      meta: { requiresAuth: true, title: 'Data Explorer' },
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

router.beforeEach((to) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.guestOnly && authStore.isAuthenticated) {
    return { name: 'dashboard' }
  }
  return true
})

export default router
