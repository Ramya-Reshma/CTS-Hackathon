import React, { useState, useMemo } from 'react'

/**
 * Interactive Geographic Intelligence Map component.
 * Inspects real dataset records for geographic attributes.
 * Renders an interactive regional risk map if geographic attributes exist;
 * otherwise displays a professional clean enterprise fallback state.
 */
export default function InteractiveRegionalMap({ anomalies = [], currentRun = null }) {
  const [selectedRegion, setSelectedRegion] = useState(null)
  const [zoomLevel, setZoomLevel] = useState(1)

  // Inspect dataset records for geographic fields
  const geoData = useMemo(() => {
    const regionCounts = {}
    let hasGeo = false

    anomalies.forEach(a => {
      const fr = a.full_record || {}
      const state = fr.State || fr.state || fr.Provider_State || fr.provider_state || fr.Region || fr.region || null
      if (state) {
        hasGeo = true
        regionCounts[state] = (regionCounts[state] || 0) + 1
      }
    })

    return { hasGeo, regionCounts }
  }, [anomalies])

  if (!geoData.hasGeo) {
    return (
      <div className="ml-panel">
        <div className="ml-panel-header">
          <div>
            <h2>Geographic / Regional Intelligence</h2>
            <p>Spatial surveillance of operational risk, claims volume, and SLA exposure</p>
          </div>
        </div>
        <div style={{ padding: '36px 24px', textAlign: 'center', background: 'var(--surface-inset)' }}>
          <div
            style={{
              width: '46px',
              height: '46px',
              borderRadius: '50%',
              background: '#e0f2fe',
              color: '#0369a1',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '12px',
            }}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />
              <path d="M2 12h20" />
            </svg>
          </div>
          <h3 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--navy-900)', marginBottom: '6px' }}>
            Geographic Intelligence
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--gray-500)', maxWidth: '520px', margin: '0 auto', lineHeight: 1.5 }}>
            No geographic attributes are available for this run.
          </p>
          <div style={{ fontSize: '11px', color: 'var(--gray-400)', marginTop: '8px' }}>
            Regional risk mapping and provider geospatial clustering will automatically activate when geographic coordinates or State/ZIP attributes are ingested.
          </div>
        </div>
      </div>
    )
  }

  // If geographic data IS found in the dataset, render interactive map
  return (
    <div className="ml-panel">
      <div className="ml-panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2>Operational Risk by Geography</h2>
          <p>Regional claims concentration and geospatial incident distribution</p>
        </div>
        <div style={{ display: 'flex', gap: '6px' }}>
          <button className="ml-filter-pill" onClick={() => setZoomLevel(z => Math.min(2.5, z + 0.25))}>+</button>
          <button className="ml-filter-pill" onClick={() => setZoomLevel(z => Math.max(1, z - 0.25))}>−</button>
          <button className="ml-filter-pill" onClick={() => { setZoomLevel(1); setSelectedRegion(null) }}>Reset</button>
        </div>
      </div>
      <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <div style={{ width: '100%', maxWidth: '700px', height: '320px', position: 'relative', overflow: 'hidden', border: '1px solid #e2e8f0', borderRadius: '8px', background: '#f8fafc' }}>
          <svg width="100%" height="100%" viewBox="0 0 800 450" style={{ transform: `scale(${zoomLevel})`, transformOrigin: 'center center', transition: 'transform 0.2s ease' }}>
            {/* Render regions */}
            {Object.entries(geoData.regionCounts).map(([region, count], idx) => (
              <g key={region} onClick={() => setSelectedRegion({ region, count })}>
                <circle
                  cx={150 + (idx * 80) % 600}
                  cy={100 + (idx * 50) % 300}
                  r={Math.min(30, Math.max(12, count * 3))}
                  fill="#2563eb"
                  fillOpacity={0.65}
                  stroke="#1e3a8a"
                  strokeWidth="2"
                  style={{ cursor: 'pointer' }}
                />
                <text
                  x={150 + (idx * 80) % 600}
                  y={105 + (idx * 50) % 300}
                  textAnchor="middle"
                  fill="#ffffff"
                  fontSize="11"
                  fontWeight="bold"
                >
                  {region}
                </text>
              </g>
            ))}
          </svg>
          {selectedRegion && (
            <div style={{ position: 'absolute', bottom: '12px', left: '12px', background: '#ffffff', padding: '8px 12px', borderRadius: '6px', boxShadow: '0 2px 8px rgba(0,0,0,0.1)', border: '1px solid #cbd5e1' }}>
              <strong>{selectedRegion.region}</strong>: {selectedRegion.count} records
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
