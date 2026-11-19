import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from '@/App.vue'
import router from '@/router'
import { configureHttpAuth, httpClient } from '@/api/http'
import { useAuthStore } from '@/stores/auth.store'
import '@/style.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

const authStore = useAuthStore(pinia)

configureHttpAuth(httpClient, {
  getAccessToken: () => authStore.accessToken,
  getRefreshToken: () => authStore.refreshToken,
  onTokensRefreshed: (response) => authStore.applySession(response),
  onAuthFailure: () => {
    authStore.clearSession()
    if (router.currentRoute.value.name !== 'login') {
      void router.push({ name: 'login' })
    }
  },
})

app.mount('#app')
