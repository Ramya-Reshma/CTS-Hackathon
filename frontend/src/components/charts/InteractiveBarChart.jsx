import React, { useState } from 'react'

/**
 * Interactive Horizontal Bar Chart with hover tooltips and interactive value inspection.
 * @param {Array} data - Array of { label: string, value: number, color?: string, sublabel?: string, count?: number }
 * @param {string} title - Chart title
 * @param {string} unit - Unit suffix (e.g., 'records')
 */
export default function InteractiveBarChart({
  data = [],
  unit = 'records',
  maxVal = null,
}) {
  const [hoveredIdx, setHoveredIdx] = useState(null)

  const validData = data.filter(d => Number(d.value) >= 0)
  const total = validData.reduce((acc, curr) => acc + Number(curr.value), 0)
  const calculatedMax = maxVal || Math.max(...validData.map(d => Number(d.value)), 1)

  if (validData.length === 0) {
    return (
      <div style={{ padding: '24px', textAlign: 'center', color: '#94a3b8', fontSize: '13px' }}>
        No category data available
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', width: '100%' }}>
      {validData.map((item, idx) => {
        const isHovered = hoveredIdx === idx
        const pct = ((item.value / calculatedMax) * 100).toFixed(1)
        const sharePct = total > 0 ? ((item.value / total) * 100).toFixed(1) : '0.0'
        const barColor = item.color || '#2563eb'

        return (
          <div
            key={idx}
            onMouseEnter={() => setHoveredIdx(idx)}
            onMouseLeave={() => setHoveredIdx(null)}
            style={{
              padding: '8px 12px',
              borderRadius: '8px',
              background: isHovered ? '#f8fafc' : 'transparent',
              border: isHovered ? '1px solid #e2e8f0' : '1px solid transparent',
              transition: 'all 0.15s ease',
              cursor: 'pointer',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span
                  style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '2px',
                    backgroundColor: barColor,
                    display: 'inline-block',
                  }}
                />
                <span style={{ fontSize: '13px', fontWeight: isHovered ? 700 : 600, color: '#0f172a' }}>
                  {item.label}
                </span>
                {item.sublabel && (
                  <span style={{ fontSize: '11px', color: '#64748b' }}>
                    · {item.sublabel}
                  </span>
                )}
              </div>
              <div style={{ textAlign: 'right' }}>
                <span style={{ fontSize: '13px', fontWeight: 700, color: '#0f172a', fontFamily: 'var(--font-mono)' }}>
                  {item.value.toLocaleString()} <span style={{ fontSize: '11px', fontWeight: 400, color: '#64748b' }}>{unit}</span>
                </span>
                <span style={{ fontSize: '11px', color: '#94a3b8', marginLeft: '6px' }}>
                  ({sharePct}%)
                </span>
              </div>
            </div>

            {/* Bar Track & Fill */}
            <div
              style={{
                height: isHovered ? '10px' : '8px',
                background: '#f1f5f9',
                borderRadius: '4px',
                overflow: 'hidden',
                position: 'relative',
                transition: 'height 0.15s ease',
              }}
            >
              <div
                style={{
                  height: '100%',
                  width: `${Math.min(100, Math.max(2, pct))}%`,
                  background: isHovered ? barColor : `linear-gradient(90deg, ${barColor}, ${barColor}dd)`,
                  borderRadius: '4px',
                  transition: 'width 0.4s ease, filter 0.2s ease',
                  filter: isHovered ? 'brightness(1.1)' : 'none',
                }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}
