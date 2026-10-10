import Taro from '@tarojs/taro'

export function showToast(title: string) {
  Taro.showToast({ title, icon: 'none' })
}
