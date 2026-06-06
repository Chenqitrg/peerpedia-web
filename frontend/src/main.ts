import './assets/main.css'
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createI18n } from 'vue-i18n'
import { router } from './router'
import App from './App.vue'
import enUS from './locales/en-US.json'
import zhCN from './locales/zh-CN.json'

const savedLocale = localStorage.getItem('locale') || 'zh-CN'

const i18n = createI18n({
  legacy: false,
  locale: savedLocale,
  fallbackLocale: 'en-US',
  messages: { 'en-US': enUS, 'zh-CN': zhCN },
})

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(i18n)
app.mount('#app')
