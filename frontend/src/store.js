import { create } from 'zustand'

const isDev = window.location.port === '5173' || window.location.port === '5174'
export const API_BASE = localStorage.getItem('API_BASE') || (isDev ? 'https://newsroom-1zapway-newsroom-cloud.onrender.com' : '')

export const useStore = create((set) => ({
  // Edit State
  isEditMode: false,
  setEditMode: (val) => set({ isEditMode: val }),

  // Filters
  searchQuery: '',
  setSearchQuery: (val) => set({ searchQuery: val }),
  
  statusFilter: 'All',
  setStatusFilter: (val) => set({ statusFilter: val }),
  
  calendarDate: '',
  setCalendarDate: (val) => set({ calendarDate: val }),

  // Ingestion State
  isOrchestrating: false,
  setIsOrchestrating: (val) => set({ isOrchestrating: val }),
}))
