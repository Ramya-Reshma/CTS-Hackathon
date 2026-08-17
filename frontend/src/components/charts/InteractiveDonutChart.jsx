import React, { useState } from 'react'

/**
 * Interactive Donut Chart with hover tooltips, slice highlighting, and legend.
 * @param {Array} data - Array of { label: string, value: number, color: string, sublabel?: string }
 * @param {number} size - Chart diameter in px (default: 240)
 * @param {string} centerLabel - Text under center value (e.g., 'Total Findings')
 * @param {string|number} centerValue - Override center value
 */
export default function InteractiveDonutChart({
  data = [],
  size = 240,
  centerLabel = 'TOTAL',
  centerValue = null,
  unit = '',
}) {
  const [hoveredIdx, setHoveredIdx] = useState(null)
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 })

  const validData = data.filter(d => Number(d.value) > 0)
  const total = validData.reduce((acc, curr) => acc + Number(curr.value), 0)

  const radius = size / 2
  const strokeWidth = 28
  const innerRadius = radius - strokeWidth
  const circumference = 2 * Math.PI * innerRadius

  if (total === 0 || validData.length === 0) {
    return (
      <div style={{ height: size, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8', fontSize: '13px' }}>
        No chart data available
      </div>
    )
  }

  let accumulatedPercent = 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', position: 'relative', width: '100%' }}>
      <div style={{ position: 'relative', width: size, height: size }}>
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          style={{ transform: 'rotate(-90deg)', overflow: 'visible' }}
          onMouseLeave={() => setHoveredIdx(null)}
        >
          {validData.map((item, idx) => {
            const pct = item.value / total
            const dashArray = `${pct * circumference} ${circumference}`
            const dashOffset = -accumulatedPercent * circumference
            accumulatedPercent += pct

            const isHovered = hoveredIdx === idx
            const currentStrokeWidth = isHovered ? strokeWidth + 6 : strokeWidth

            return (
              <circle
                key={idx}
                cx={radius}
                cy={radius}
                r={innerRadius}
                fill="transparent"
                stroke={item.color || '#3b82f6'}
                strokeWidth={currentStrokeWidth}
                strokeDasharray={dashArray}
                strokeDashoffset={dashOffset}
                style={{
                  transition: 'stroke-width 0.2s ease, filter 0.2s ease',
                  cursor: 'pointer',
                  filter: isHovered ? 'drop-shadow(0 4px 8px rgba(0,0,0,0.25))' : 'none',
                }}
                onMouseEnter={(e) => {
                  setHoveredIdx(idx)
                  const rect = e.currentTarget.getBoundingClientRect()
                  setTooltipPos({ x: rect.left, y: rect.top })
                }}
              />
            )
          })}
        </svg>

        {/* Center Label Display */}
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            textAlign: 'center',
            pointerEvents: 'none',
          }}
        >
          <div style={{ fontSize: '10px', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.6px' }}>
            {hoveredIdx !== null ? validData[hoveredIdx]?.label : centerLabel}
          </div>
          <div style={{ fontSize: '22px', fontWeight: 800, color: '#0f172a', lineHeight: 1.1, marginTop: '2px' }}>
            {hoveredIdx !== null
              ? `${validData[hoveredIdx]?.value?.toLocaleString()}${unit}`
              : centerValue !== null
                ? centerValue
                : `${total.toLocaleString()}${unit}`}
          </div>
          <div style={{ fontSize: '10px', color: '#94a3b8', marginTop: '2px' }}>
            {hoveredIdx !== null
              ? `${((validData[hoveredIdx]?.value / total) * 100).toFixed(1)}% of total`
              : `${validData.length} categories`}
          </div>
        </div>
      </div>

      {/* Interactive Legend */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'center',
          gap: '12px',
          marginTop: '16px',
          width: '100%',
        }}
      >
        {validData.map((item, idx) => {
          const isHovered = hoveredIdx === idx
          const pct = ((item.value / total) * 100).toFixed(1)
          return (
            <div
              key={idx}
              onMouseEnter={() => setHoveredIdx(idx)}
              onMouseLeave={() => setHoveredIdx(null)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '4px 8px',
                borderRadius: '6px',
                background: isHovered ? '#f1f5f9' : 'transparent',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              <span
                style={{
                  width: '10px',
                  height: '10px',
                  borderRadius: '50%',
                  backgroundColor: item.color || '#3b82f6',
                  display: 'inline-block',
                }}
              />
              <span style={{ fontSize: '12px', fontWeight: 600, color: isHovered ? '#0f172a' : '#475569' }}>
                {item.label}:
              </span>
              <span style={{ fontSize: '12px', fontWeight: 700, color: '#0f172a' }}>
                {item.value.toLocaleString()} <span style={{ fontSize: '10px', color: '#64748b', fontWeight: 500 }}>({pct}%)</span>
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
