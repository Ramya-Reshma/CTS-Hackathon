/**
 * useMedlyticsData.js
 * 
 * Shared data hook for all MEDLYTICS pages.
 * Fetches from the EXISTING backend API and exposes raw backend fields.
 * Does NOT calculate or modify backend values.
 */

import { useState, useEffect } from 'react'
import { useStore } from './useStore'
import { getAnomalies, getRunInfo } from '../services/api'

export function useMedlyticsData() {
  const currentRun = useStore(state => state.currentRun)
  const [anomalies, setAnomalies] = useState([])
  const [statistics, setStatistics] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!currentRun) return

    const load = async () => {
      setIsLoading(true)
      setError(null)
      try {
        const [anomalyResult, runInfo] = await Promise.all([
          getAnomalies(currentRun.run_id, { page: 1, pageSize: 200 }),
          getRunInfo(currentRun.run_id),
        ])
        setAnomalies(anomalyResult.records || [])
        setStatistics(runInfo.statistics || null)
      } catch (err) {
        setError(err.message || 'Failed to load monitoring data')
      } finally {
        setIsLoading(false)
      }
    }

    load()
  }, [currentRun?.run_id])

  return { anomalies, statistics, isLoading, error, currentRun }
}
