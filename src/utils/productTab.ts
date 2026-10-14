import Taro from '@tarojs/taro'
import { CURRENT_PRODUCT_TABS } from '@/constants/productNavigation'

/** 导航到主 Tab。微信端保持在单页容器内；H5 沿用原页面路由。 */
export function openProductTab(tab: 'home' | 'user'): void {
  const target = CURRENT_PRODUCT_TABS.find((item) => item.key === tab) || CURRENT_PRODUCT_TABS[0]
  if (process.env.TARO_ENV === 'weapp') {
    const query = tab === 'user' ? '?tab=user' : ''
    void Taro.reLaunch({ url: `${CURRENT_PRODUCT_TABS[0].path}${query}` })
    return
  }
  void Taro.switchTab({ url: target.path })
}
