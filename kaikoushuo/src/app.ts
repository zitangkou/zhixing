import { createApp } from 'vue'
import { ensureWechatLogin } from './auth'
import './app.scss'

const App = createApp({
  onLaunch() { void ensureWechatLogin().catch(() => {}) },
  onShow() {},
})

export default App
