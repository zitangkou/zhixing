/**
 * 语音转文字：默认 Web Speech（免费），云 ASR 可配置后优先。
 * H5 可用；小程序无 Web Speech 时依赖云 ASR。
 */

import { API_BASE } from '@/utils/media'
import { getToken } from '@/utils/auth'
import { getPlatform } from '@/utils/platform'

export type AsrProvider = 'none' | 'webspeech' | 'aliyun' | 'tencent' | string

export interface AsrStatus {
  provider: AsrProvider
  cloudAvailable: boolean
  preferCloud: boolean
  hint: string
}

type SpeechHandlers = {
  onInterim?: (text: string) => void
  onFinal?: (text: string) => void
  onError?: (message: string) => void
  onStart?: () => void
  onEnd?: () => void
}

type AnyRecognition = {
  lang: string
  continuous: boolean
  interimResults: boolean
  maxAlternatives: number
  onstart: (() => void) | null
  onerror: ((ev: { error: string }) => void) | null
  onresult: ((ev: any) => void) | null
  onend: (() => void) | null
  start: () => void
  stop: () => void
}

let cachedStatus: AsrStatus | null = null
let statusFetchedAt = 0

function getSpeechRecognitionCtor(): (new () => AnyRecognition) | null {
  if (typeof window === 'undefined') return null
  const w = window as any
  return w.SpeechRecognition || w.webkitSpeechRecognition || null
}

export function isWebSpeechSupported(): boolean {
  return getPlatform() === 'h5' && !!getSpeechRecognitionCtor()
}

export async function fetchAsrStatus(force = false): Promise<AsrStatus> {
  const now = Date.now()
  if (!force && cachedStatus && now - statusFetchedAt < 60_000) return cachedStatus
  const fallback: AsrStatus = {
    provider: 'webspeech',
    cloudAvailable: false,
    preferCloud: false,
    hint: '浏览器语音识别（免费）',
  }
  try {
    const token = getToken()
    const res = await fetch(`${API_BASE}/api/asr/status`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) throw new Error('status fail')
    const body = await res.json()
    if (body?.code === 0 && body.data) {
      cachedStatus = body.data as AsrStatus
      statusFetchedAt = now
      return cachedStatus
    }
  } catch {
    /* ignore */
  }
  cachedStatus = fallback
  statusFetchedAt = now
  return fallback
}

/** 拼接识别结果到原有文本 */
export function appendSpeechText(current: string, incoming: string): string {
  const a = (current || '').trimEnd()
  const b = (incoming || '').trim()
  if (!b) return current || ''
  if (!a) return b
  if (/[，。！？；、：…\n]$/.test(a) || /^[，。！？；、：…]/.test(b)) {
    return `${a}${b}`
  }
  if (/[A-Za-z0-9]$/.test(a) && /^[A-Za-z0-9]/.test(b)) {
    return `${a} ${b}`
  }
  return `${a}${b}`
}

/** 轻度清洗口语填充词 */
export function applyHotwords(text: string, _hotwords: string[] = []): string {
  if (!text) return text
  let out = text.replace(/[ \t]+/g, '')
  out = out.replace(/(嗯+|啊+|那个|就是说)/g, '')
  return out.trim()
}

export type SpeechSession = {
  stop: () => void
}

/** Web Speech：点一次开始，再点停止 */
export function startWebSpeech(
  handlers: SpeechHandlers,
  opts?: { lang?: string },
): SpeechSession | null {
  const Ctor = getSpeechRecognitionCtor()
  if (!Ctor) {
    handlers.onError?.('当前浏览器不支持免费语音识别，可改用 Chrome/Edge，或配置云 ASR')
    return null
  }
  const rec = new Ctor()
  rec.lang = opts?.lang || 'zh-CN'
  rec.continuous = true
  rec.interimResults = true
  rec.maxAlternatives = 3

  let finalBuf = ''
  let stopped = false

  rec.onstart = () => handlers.onStart?.()
  rec.onerror = (ev) => {
    const map: Record<string, string> = {
      'not-allowed': '麦克风权限被拒绝',
      'no-speech': '没有听清，请靠近麦克风再说一次',
      'audio-capture': '无法使用麦克风',
      network: '识别服务网络异常',
      aborted: '',
    }
    const msg = map[ev.error] ?? `识别失败：${ev.error}`
    if (msg) handlers.onError?.(msg)
  }
  rec.onresult = (ev: any) => {
    let interim = ''
    for (let i = ev.resultIndex; i < ev.results.length; i++) {
      const r = ev.results[i]
      const alt = pickBestAlternative(r)
      if (r.isFinal) {
        finalBuf = appendSpeechText(finalBuf, alt)
        handlers.onFinal?.(finalBuf)
      } else {
        interim += alt
      }
    }
    if (interim) handlers.onInterim?.(appendSpeechText(finalBuf, interim))
  }
  rec.onend = () => {
    if (!stopped) {
      try {
        rec.start()
        return
      } catch {
        /* stopped */
      }
    }
    handlers.onEnd?.()
  }

  try {
    rec.start()
  } catch (e) {
    handlers.onError?.(e instanceof Error ? e.message : '无法启动语音识别')
    return null
  }

  return {
    stop: () => {
      stopped = true
      try {
        rec.stop()
      } catch {
        /* ignore */
      }
    },
  }
}

function pickBestAlternative(result: any): string {
  let best = result[0]?.transcript || ''
  let bestConf = result[0]?.confidence ?? 0
  for (let i = 1; i < (result.length || 0); i++) {
    const c = result[i]?.confidence ?? 0
    if (c > bestConf) {
      bestConf = c
      best = result[i].transcript
    }
  }
  return (best || '').trim()
}

/** MediaRecorder 录一段 → 上传云 ASR（需后端配置） */
export async function recordAndTranscribeCloud(
  handlers: SpeechHandlers,
  opts?: { maxMs?: number },
): Promise<SpeechSession | null> {
  if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
    handlers.onError?.('当前环境无法录音')
    return null
  }
  let stream: MediaStream
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  } catch {
    handlers.onError?.('麦克风权限被拒绝')
    return null
  }

  const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
    ? 'audio/webm;codecs=opus'
    : MediaRecorder.isTypeSupported('audio/webm')
      ? 'audio/webm'
      : ''
  const chunks: BlobPart[] = []
  const recorder = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream)
  let stopped = false

  recorder.ondataavailable = (e) => {
    if (e.data.size) chunks.push(e.data)
  }

  const finish = async () => {
    stream.getTracks().forEach((t) => t.stop())
    if (!chunks.length) {
      handlers.onError?.('没有录到声音')
      handlers.onEnd?.()
      return
    }
    const blob = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' })
    try {
      const text = await uploadAsrBlob(blob)
      if (text) handlers.onFinal?.(text)
      else handlers.onError?.('云识别未返回文字')
    } catch (e) {
      handlers.onError?.(e instanceof Error ? e.message : '云识别失败')
    } finally {
      handlers.onEnd?.()
    }
  }

  recorder.onstop = () => {
    void finish()
  }

  handlers.onStart?.()
  recorder.start(200)
  const maxMs = opts?.maxMs ?? 60_000
  const timer = setTimeout(() => {
    if (!stopped && recorder.state === 'recording') {
      stopped = true
      recorder.stop()
    }
  }, maxMs)

  return {
    stop: () => {
      clearTimeout(timer)
      if (stopped) return
      stopped = true
      if (recorder.state === 'recording') recorder.stop()
      else {
        stream.getTracks().forEach((t) => t.stop())
        handlers.onEnd?.()
      }
    },
  }
}

async function uploadAsrBlob(blob: Blob): Promise<string> {
  const token = getToken()
  const form = new FormData()
  const ext = blob.type.includes('wav') ? 'wav' : 'webm'
  form.append('file', new File([blob], `speech.${ext}`, { type: blob.type || 'audio/webm' }))
  const res = await fetch(`${API_BASE}/api/asr/transcribe`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  })
  const body = await res.json()
  if (body?.code !== 0) {
    throw new Error(body?.message || '转写失败')
  }
  return String(body?.data?.text || '').trim()
}

/** 智能启动：默认免费 Web Speech；云可用且 preferCloud 时走云 */
export async function startSmartSpeech(handlers: SpeechHandlers): Promise<SpeechSession | null> {
  const status = await fetchAsrStatus()
  if (status.preferCloud && status.cloudAvailable) {
    return recordAndTranscribeCloud(handlers)
  }
  if (isWebSpeechSupported()) {
    return startWebSpeech(handlers)
  }
  if (status.cloudAvailable) {
    return recordAndTranscribeCloud(handlers)
  }
  handlers.onError?.(
    status.hint || '当前环境不支持语音输入。请使用 Chrome/Edge，或在服务端配置 ASR_PROVIDER',
  )
  return null
}
