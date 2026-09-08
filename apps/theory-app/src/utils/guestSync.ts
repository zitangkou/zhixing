import Taro from '@tarojs/taro'
import { api, type GuestLearningRecord } from '@/api'

const PREFIX = 'theory-learning:'
const DEVICE_KEY = 'zhixing_guest_device_id'

function deviceId(): string {
  const existing = String(Taro.getStorageSync(DEVICE_KEY) || '')
  if (/^[A-Za-z0-9_-]{8,64}$/.test(existing)) return existing
  const created = `dev_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 12)}`
  Taro.setStorageSync(DEVICE_KEY, created)
  return created
}

function parseKey(key: string): { contentId: string; revision: string } | null {
  const rest = key.slice(PREFIX.length)
  const split = rest.lastIndexOf(':')
  if (split < 1 || split === rest.length - 1) return null
  return { contentId: rest.slice(0, split), revision: rest.slice(split + 1) }
}

function collect(): GuestLearningRecord[] {
  const keys = Taro.getStorageInfoSync().keys || []
  const output: GuestLearningRecord[] = []
  for (const key of keys.filter(item => item.startsWith(PREFIX))) {
    const identity = parseKey(key)
    const payload = Taro.getStorageSync(key)
    if (!identity || !payload || typeof payload !== 'object') continue
    const updatedAt = typeof payload.updatedAt === 'string' ? payload.updatedAt : new Date().toISOString()
    if (!payload.updatedAt) Taro.setStorageSync(key, { ...payload, updatedAt })
    output.push({
      recordType: 'theory_article_quiz',
      ...identity,
      payload: { ...payload, updatedAt },
      updatedAt,
    })
  }
  return output
}

function applyRemote(records: GuestLearningRecord[]) {
  for (const record of records) {
    const key = `${PREFIX}${record.contentId}:${record.revision}`
    const local = Taro.getStorageSync(key)
    const localTime = Date.parse(typeof local?.updatedAt === 'string' ? local.updatedAt : '') || 0
    const remoteTime = Date.parse(record.updatedAt) || 0
    if (remoteTime > localTime) Taro.setStorageSync(key, { ...record.payload, updatedAt: record.updatedAt })
  }
}

export async function syncGuestLearning(): Promise<void> {
  try {
    const records = collect()
    const batches = records.length ? Array.from({ length: Math.ceil(records.length / 100) }, (_, index) => records.slice(index * 100, index * 100 + 100)) : [[]]
    for (const batch of batches) {
      const response = await api.mergeGuestRecords(deviceId(), batch)
      if (response.code === 0 && response.data) applyRemote(response.data.records)
    }
  } catch {
    // 登录不能被同步失败阻断；下次主动登录会再次幂等合并。
  }
}
