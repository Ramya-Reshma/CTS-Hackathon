import React, { useState } from 'react'
import MedlyticsSidebar from '../components/MedlyticsSidebar'
import MedlyticsHeader from '../components/MedlyticsHeader'
import OverviewPage from '../components/pages/OverviewPage'
import AnomalyPage from '../components/pages/AnomalyPage'
import SLARiskPage from '../components/pages/SLARiskPage'
import DataQualityPage from '../components/pages/DataQualityPage'
import RecommendationPage from '../components/pages/RecommendationPage'
import UploadsPage from '../components/pages/UploadsPage'
import './MedlyticsApp.css'

export const NAV_PAGES = [
  { id: 'overview',       label: 'Overview',              icon: 'overview' },
  { id: 'anomaly',        label: 'Anomaly Detection',     icon: 'anomaly' },
  { id: 'sla',            label: 'SLA Risk',               icon: 'sla' },
  { id: 'quality',        label: 'Data Quality',           icon: 'quality' },
  { id: 'recommendation', label: 'Recommendation Engine',  icon: 'recommendation' },
  { id: 'uploads',        label: 'Uploads',                icon: 'uploads' },
]

export default function MedlyticsApp({ user, onLogout }) {
  const [activePage, setActivePage] = useState('overview')
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const pageMap = {
    overview:       <OverviewPage onNavigateToUploads={() => setActivePage('uploads')} />,
    anomaly:        <AnomalyPage />,
    sla:            <SLARiskPage />,
    quality:        <DataQualityPage />,
    recommendation: <RecommendationPage />,
    uploads:        <UploadsPage onNavigateToOverview={() => setActivePage('overview')} />,
  }

  return (
    <div className="medlytics-shell">
      <MedlyticsSidebar
        activePage={activePage}
        onNavigate={(id) => { setActivePage(id); setSidebarOpen(false) }}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        user={user}
        onLogout={onLogout}
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
