import { create } from 'zustand'

const isDev = window.location.port === '5173'
export const API_BASE = isDev ? 'http://localhost:8000' : ''

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
}))
