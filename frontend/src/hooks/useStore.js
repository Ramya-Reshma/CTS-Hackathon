import { create } from 'zustand'

/**
 * Main application store using Zustand
 * Manages:
 * - Current analysis run data
 * - Anomalies list
 * - Filters and pagination
 * - Loading states
 */
export const useStore = create((set, get) => ({
  // Current run data
  currentRun: null,
  setCurrentRun: (run) => set({ currentRun: run }),

  // Anomalies list
  anomalies: [],
  setAnomalies: (anomalies) => set({ anomalies }),

  // Pagination
  page: 1,
  pageSize: 50,
  totalAnomalies: 0,
  setPage: (page) => set({ page }),
  setPageSize: (pageSize) => set({ pageSize }),
  setTotalAnomalies: (total) => set({ totalAnomalies: total }),

  // Filters
  severityFilter: null,
  setSeverityFilter: (severity) => set({ severityFilter: severity, page: 1 }),

  searchQuery: '',
  setSearchQuery: (query) => set({ searchQuery: query, page: 1 }),

  // Loading states
  isLoading: false,
  setIsLoading: (loading) => set({ isLoading: loading }),

  isUploading: false,
  setIsUploading: (uploading) => set({ isUploading: uploading }),

  // Error state
  error: null,
  setError: (error) => set({ error }),
  clearError: () => set({ error: null }),

  // Selected anomaly detail
  selectedAnomaly: null,
  setSelectedAnomaly: (anomaly) => set({ selectedAnomaly: anomaly }),

  // Statistics
  statistics: null,
  setStatistics: (stats) => set({ statistics: stats }),

  // Reset store
  reset: () => set({
    currentRun: null,
    anomalies: [],
    page: 1,
    pageSize: 50,
    totalAnomalies: 0,
    severityFilter: null,
    searchQuery: '',
    isLoading: false,
    isUploading: false,
    error: null,
    selectedAnomaly: null,
    statistics: null,
  }),
}))
