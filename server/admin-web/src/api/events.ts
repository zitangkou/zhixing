import http, { getData } from './http'

export interface EventItem {
  id: string
  userId: string
  title: string
  eventDate: string
  place: string
  coreContent: string
  note: string
  knowledgeNodeId: string
  knowledgeTreeKey: string
  knowledgePath: string
  createdAt: string
  updatedAt: string
}

export interface EventHub {
  totalEvents: number
  recentEvents: EventItem[]
  frameworkGroups: { treeKey: string; label: string; count: number }[]
}

export const listEvents = (params?: { userId?: string; treeKey?: string; q?: string }) =>
  getData<EventItem[]>(http.get('/admin/events/list', { params }))

export const getEventHub = (userId: string) =>
  getData<EventHub>(http.get('/admin/events/hub', { params: { userId } }))

export const updateEvent = (id: string, data: Record<string, unknown>) =>
  getData<EventItem>(http.put(`/admin/events/${id}`, data))

export const deleteEvent = (id: string) => getData(http.delete(`/admin/events/${id}`))
