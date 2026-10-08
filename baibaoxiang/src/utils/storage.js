import Taro from '@tarojs/taro'

const KEYS = {
  profile: 'baibaoxiang.profile',
  favorites: 'baibaoxiang.favorites',
  history: 'baibaoxiang.history',
  settings: 'baibaoxiang.settings',
  token: 'baibaoxiang.token',
  user: 'baibaoxiang.user',
}

function read(key, fallback) {
  try {
    return Taro.getStorageSync(key) || fallback
  } catch {
    return fallback
  }
}

function write(key, value) {
  try {
    Taro.setStorageSync(key, value)
    return true
  } catch {
    return false
  }
}

export const storage = {
  profile: () => read(KEYS.profile, { nickname: '', tagline: '' }),
  saveProfile: (value) => write(KEYS.profile, value),
  favorites: () => read(KEYS.favorites, []),
  saveFavorites: (value) => write(KEYS.favorites, value),
  history: () => read(KEYS.history, []),
  saveHistory: (value) => write(KEYS.history, value),
  settings: () => read(KEYS.settings, { reminders: false, compactMode: false }),
  saveSettings: (value) => write(KEYS.settings, value),
  token: () => read(KEYS.token, ''),
  saveSession: (token, user) => write(KEYS.token, token) && write(KEYS.user, user),
  user: () => read(KEYS.user, null),
  clearSession: () => {
    try { Taro.removeStorageSync(KEYS.token); Taro.removeStorageSync(KEYS.user) } catch {}
  },
  clearAll: () => {
    Object.values(KEYS).forEach((key) => {
      try { Taro.removeStorageSync(key) } catch {}
    })
  },
}
