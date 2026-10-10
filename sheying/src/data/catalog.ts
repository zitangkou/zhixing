import { ref } from 'vue'
import { fetchPhotographyCatalog } from '@/api/photography'
import { lessons as defaultLessons, roadmap as defaultRoadmap, type Lesson, type RoadmapStage } from '@/data/lessons'

export const lessons = ref<Lesson[]>(defaultLessons)
export const roadmap = ref<RoadmapStage[]>(defaultRoadmap)
let loading: Promise<void> | null = null
let loaded = false

export function loadCatalog(force = false): Promise<void> {
  if (loading) return loading
  if (loaded && !force) return Promise.resolve()
  loading = fetchPhotographyCatalog()
    .then((catalog) => {
      if (catalog?.lessons?.length) lessons.value = catalog.lessons
      if (catalog?.stages?.length) roadmap.value = catalog.stages
    })
    .catch(() => { /* API 不可用时保留内置课程，保证离线演示可用。 */ })
    .finally(() => { loaded = true; loading = null })
  return loading
}
