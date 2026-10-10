import Taro from '@tarojs/taro'

export type PracticeNote = {
  id: string
  lessonId: string
  lessonTitle: string
  subject: string
  observation: string
  nextTry: string
  date: string
}

export const PRACTICE_NOTES_KEY = 'gy-practice-notes'

export function readPracticeNotes(): PracticeNote[] {
  const value = Taro.getStorageSync(PRACTICE_NOTES_KEY)
  return Array.isArray(value) ? value : []
}

export function savePracticeNotes(notes: PracticeNote[]) {
  Taro.setStorageSync(PRACTICE_NOTES_KEY, notes)
}
