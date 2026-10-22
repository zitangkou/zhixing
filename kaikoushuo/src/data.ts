import Taro from '@tarojs/taro'
import { reactive } from 'vue'
import { API_BASE_URL } from '@/config'
import { ensureWechatLogin, getAccessToken } from '@/auth'

export type Lesson = { id: string; serverId?: string; sceneId?: string; sceneTitle?: string; title: string; level: string; minutes: number; goal: string; mediaType?: 'text' | 'audio' | 'video' | 'video_audio'; audioUrl?: string; videoUrl?: string; posterUrl?: string; sourceUrl?: string; rightsStatus?: string; startSeconds?: number; endSeconds?: number; dialogueAudioUrl?: string; dialogue: { speaker: string; en: string; zh: string; audioUrl?: string; startSeconds?: number; endSeconds?: number }[]; phrases: { en: string; zh: string }[]; prompt: string }

export const lessons = reactive<Lesson[]>([
  { id: 'coffee-order', title: '在咖啡店点单', level: 'A1 入门', minutes: 8, goal: '点一杯饮品，并说明冷热和大小偏好。', dialogue: [
    { speaker: 'Barista', en: 'Hi! What can I get for you?', zh: '你好，想来点什么？' },
    { speaker: 'You', en: 'Could I have a small iced latte, please?', zh: '请给我一杯小杯冰拿铁。' },
    { speaker: 'Barista', en: 'Sure. Would you like anything else?', zh: '好的，还需要别的吗？' },
    { speaker: 'You', en: 'That’s all, thanks.', zh: '就这些，谢谢。' },
  ], phrases: [
    { en: 'Could I have ..., please?', zh: '礼貌点单：请给我……' },
    { en: 'Would you like anything else?', zh: '还需要别的吗？' },
    { en: 'That’s all, thanks.', zh: '就这些，谢谢。' },
  ], prompt: '现在换成一杯中杯热美式。请不看完整对话，说出你的点单。' },
  { id: 'introduce-yourself', title: '轻松介绍自己', level: 'A1 入门', minutes: 6, goal: '用三句话介绍姓名、来自哪里和一个兴趣。', dialogue: [
    { speaker: 'Alex', en: 'Hey, I’m Alex. Nice to meet you.', zh: '嗨，我叫 Alex。很高兴认识你。' },
    { speaker: 'You', en: 'Nice to meet you too. I’m Mia.', zh: '我也很高兴认识你。我叫 Mia。' },
    { speaker: 'Alex', en: 'Where are you from?', zh: '你来自哪里？' },
    { speaker: 'You', en: 'I’m from Chengdu. I love hiking.', zh: '我来自成都。我喜欢徒步。' },
  ], phrases: [
    { en: 'Nice to meet you.', zh: '很高兴认识你。' },
    { en: 'I’m from ...', zh: '我来自……' },
    { en: 'I love ...', zh: '我喜欢……' },
  ], prompt: '请用自己的真实信息介绍姓名、所在城市和一个兴趣。' },
  { id: 'ask-directions', title: '问路与确认方向', level: 'A2 日常', minutes: 9, goal: '礼貌询问地点，并确认步行方向。', dialogue: [
    { speaker: 'You', en: 'Excuse me, how do I get to the station?', zh: '打扰一下，请问去车站怎么走？' },
    { speaker: 'Local', en: 'Go straight and turn left at the lights.', zh: '直走，在红绿灯处左转。' },
    { speaker: 'You', en: 'Is it far from here?', zh: '离这里远吗？' },
    { speaker: 'Local', en: 'No, it’s about a ten-minute walk.', zh: '不远，步行大约十分钟。' },
  ], phrases: [
    { en: 'How do I get to ...?', zh: '请问去……怎么走？' },
    { en: 'Is it far from here?', zh: '离这里远吗？' },
    { en: 'Go straight and turn ...', zh: '直走，然后……转。' },
  ], prompt: '把目的地换成博物馆，再用自己的话问路并追问需要多久。' },
])

export const progressKey = 'yanyu-progress-v1'
const learnerKey = 'yanyu-learner-id-v1'
const pendingAttemptsKey = 'yanyu-pending-attempts-v1'
export function readProgress(): string[] {
  try { return JSON.parse(Taro.getStorageSync(progressKey) || '[]') as string[] } catch { return [] }
}
function getLearnerId(): string {
  let id = Taro.getStorageSync(learnerKey) as string
  if (!id) {
    id = `yy-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
    Taro.setStorageSync(learnerKey, id)
  }
  return id
}

/** 公开课程不依赖登录；接口不可用时使用内置原创样例。 */
export async function loadLessons(): Promise<void> {
  try {
    const token = getAccessToken()
    const response = await Taro.request({ url: `${API_BASE_URL}/english/scenes`, header: { 'X-Product-Key': 'general', ...(token ? { Authorization: `Bearer ${token}` } : {}) } })
    const payload = response.data as { code?: number; data?: Array<{ id: string; title: string; units?: Array<Record<string, any>> }> }
    if (payload.code !== 0 || !Array.isArray(payload.data)) return
    const remote = payload.data.flatMap((scene) => (scene.units || []).map((unit) => {
      const content = (unit.content || {}) as Record<string, any>
      const media = (content.media || {}) as Record<string, any>
      const transcript = Array.isArray(content.transcript) ? content.transcript : content.dialogue
      return ({
      id: lessons.find((local) => local.title === unit.title)?.id || unit.id as string,
      serverId: unit.id as string, sceneId: scene.id, sceneTitle: scene.title,
      title: String(unit.title || ''), level: String(unit.level || 'A1 入门'), minutes: Number(unit.durationMin || 8), goal: String(unit.goal || ''),
      mediaType: (media.type || (content.dialogueAudioUrl ? 'audio' : 'text')) as Lesson['mediaType'],
      audioUrl: String(media.audioUrl || content.dialogueAudioUrl || ''), videoUrl: String(media.videoUrl || ''), posterUrl: String(media.posterUrl || ''),
      sourceUrl: String(media.sourceUrl || ''), rightsStatus: String(media.rightsStatus || ''),
      startSeconds: Number(media.startSeconds || 0), endSeconds: Number(media.endSeconds || 0),
      dialogueAudioUrl: String(media.audioUrl || content.dialogueAudioUrl || ''),
      dialogue: Array.isArray(transcript) ? transcript : [],
      phrases: Array.isArray(content.phrases) ? content.phrases : [],
      prompt: String(content.prompt || content.tasks?.roleplayPrompt || content.tasks?.retellPrompt || ''),
    })
    }))
    if (remote.length) lessons.splice(0, lessons.length, ...remote)
  } catch {
    // Offline fallback keeps the bundled sample lessons available.
  }
}

export type StudyResult = 'independent' | 'hinted' | 'not_yet' | 'unknown'
export type LearnerProgress = { completedUnitIds: string[]; dueReviews: { unitId: string; title: string; level: string; nextReviewAt: string; reviewStage: number }[]; completedUnits: number }

function requestHeaders() {
  const token = getAccessToken()
  return { 'X-Product-Key': 'general', ...(token ? { Authorization: `Bearer ${token}` } : { 'X-User-Id': getLearnerId() }) }
}

export async function loadLearnerProgress(): Promise<LearnerProgress | null> {
  try {
    const response = await Taro.request({ url: `${API_BASE_URL}/english/progress`, header: requestHeaders() })
    const payload = response.data as { code?: number; data?: LearnerProgress }
    if (payload.code !== 0 || !payload.data) return null
    const mapped = payload.data.completedUnitIds.flatMap((id) => {
      const lesson = lessons.find((item) => item.serverId === id)
      return lesson ? [lesson.id] : []
    })
    const merged = new Set([...readProgress(), ...mapped])
    Taro.setStorageSync(progressKey, JSON.stringify([...merged]))
    return payload.data
  } catch { return null }
}

export async function markLessonComplete(lesson: Lesson, attemptId: string, result: StudyResult): Promise<boolean> {
  if (!lesson.serverId) return true
  const attempt = { unitId: lesson.serverId || lesson.id, attemptId, result }
  const pending = (() => { try { return JSON.parse(Taro.getStorageSync(pendingAttemptsKey) || '[]') as typeof attempt[] } catch { return [] as typeof attempt[] } })()
  if (!pending.some((item) => item.attemptId === attemptId)) pending.push(attempt)
  Taro.setStorageSync(pendingAttemptsKey, JSON.stringify(pending))
  return flushPendingAttempts()
}

export async function flushPendingAttempts(): Promise<boolean> {
  let pending: { unitId: string; attemptId: string; result: StudyResult }[]
  try { pending = JSON.parse(Taro.getStorageSync(pendingAttemptsKey) || '[]') } catch { pending = [] }
  if (!pending.length) return true
  try { await ensureWechatLogin() } catch { /* the local learner identity can still store anonymous progress */ }
  const remaining = [] as typeof pending
  for (const attempt of pending) {
    const lesson = lessons.find((item) => item.serverId === attempt.unitId || item.id === attempt.unitId)
    if (!lesson?.serverId) { remaining.push(attempt); continue }
    try {
      const response = await Taro.request({
        url: `${API_BASE_URL}/english/units/${lesson.serverId}/complete`, method: 'POST',
        data: { attempt_id: attempt.attemptId, result: attempt.result }, header: requestHeaders(),
      })
      const payload = response.data as { code?: number }
      if (response.statusCode < 200 || response.statusCode >= 300 || payload.code !== 0) remaining.push(attempt)
    } catch { remaining.push(attempt) }
  }
  Taro.setStorageSync(pendingAttemptsKey, JSON.stringify(remaining))
  return remaining.length === 0
}

export async function syncProgressAfterLogin(): Promise<void> {
  try { await ensureWechatLogin() } catch { return }
  const remote = await loadLearnerProgress()
  const syncedIds = new Set(remote?.completedUnitIds || [])
  // Carry forward locally completed lessons once the learner has an account.
  for (const localId of readProgress()) {
    const lesson = lessons.find((item) => item.id === localId)
    if (!lesson?.serverId) continue
    const migrationId = `local-sync-${lesson.serverId}`
    if (syncedIds.has(lesson.serverId)) continue
    const ok = await markLessonComplete(lesson, migrationId, 'unknown')
    if (!ok) break
    syncedIds.add(lesson.serverId)
  }
  await flushPendingAttempts()
  await loadLearnerProgress()
}
