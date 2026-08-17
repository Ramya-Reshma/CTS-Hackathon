import React, { useState } from 'react'
import { useStore } from '../hooks/useStore'
import { getAnomalies, getRunInfo, downloadResults } from '../services/api'
import MedlyticsSidebar from '../components/MedlyticsSidebar'
import MedlyticsHeader from '../components/MedlyticsHeader'
import OverviewPage from '../components/pages/OverviewPage'
import AnomalyPage from '../components/pages/AnomalyPage'
import SLARiskPage from '../components/pages/SLARiskPage'
import DataQualityPage from '../components/pages/DataQualityPage'
import SLASummaryPage from '../components/pages/SLASummaryPage'
import './MedlyticsApp.css'

export const NAV_PAGES = [
  { id: 'overview',  label: 'Overview',           icon: 'overview' },
  { id: 'anomaly',   label: 'Anomaly Detection',  icon: 'anomaly' },
  { id: 'sla',       label: 'SLA Risk',            icon: 'sla' },
  { id: 'quality',   label: 'Data Quality',        icon: 'quality' },
  { id: 'slasummary',label: 'SLA Summary',         icon: 'slasummary' },
]

export default function MedlyticsApp() {
  const [activePage, setActivePage] = useState('overview')
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const pageMap = {
    overview:   <OverviewPage />,
    anomaly:    <AnomalyPage />,
    sla:        <SLARiskPage />,
    quality:    <DataQualityPage />,
    slasummary: <SLASummaryPage />,
  }

  return (
    <div className="medlytics-shell">
      <MedlyticsSidebar
        activePage={activePage}
        onNavigate={(id) => { setActivePage(id); setSidebarOpen(false) }}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />
      <div className="medlytics-main">
        <MedlyticsHeader
          activePage={activePage}
          onMenuClick={() => setSidebarOpen(o => !o)}
        />
        <div className="medlytics-content">
          {pageMap[activePage] || <OverviewPage />}
        </div>
      </div>
    </div>
  )
}
