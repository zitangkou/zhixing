import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Taro from '@tarojs/taro'
import '@nutui/nutui-taro/dist/style.css'
import './app.scss'

const tabIcons = ['today', 'study', 'practice', 'profile']

function syncH5TabBarIcons() {
  if (process.env.TARO_ENV !== 'h5') return
  const base = APP_PUBLIC_PATH.endsWith('/') ? APP_PUBLIC_PATH : `${APP_PUBLIC_PATH}/`
  tabIcons.forEach((name, index) => {
    void Taro.setTabBarItem({
      index,
      iconPath: `${base}static/images/${name}.png`,
      selectedIconPath: `${base}static/images/${name}-active.png`,
    })
  })
}

const app = createApp({
  onShow() {
    setTimeout(syncH5TabBarIcons, 0)
  },
})
app.use(createPinia())

export default app
