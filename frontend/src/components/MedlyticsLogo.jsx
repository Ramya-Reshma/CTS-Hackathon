import React from 'react'

/**
 * Official MEDLYTICS Enterprise Logo
 * Features:
 * - Deep navy magnifying glass with angled handle
 * - Ascending cyan/light-blue analytics bar columns
 * - Upward breakout trend arrow
 * - Bold modern MEDLYTICS wordmark
 */
export default function MedlyticsLogo({
  size = 36,
  showText = true,
  textColor = '#0f172a',
  layout = 'horizontal', // 'horizontal' | 'vertical'
}) {
  const iconHeight = size
  const iconWidth = Math.round(size * 1.05)

  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        flexDirection: layout === 'vertical' ? 'column' : 'row',
        gap: layout === 'vertical' ? '6px' : '10px',
        textDecoration: 'none',
        userSelect: 'none',
      }}
    >
      {/* Precision Vector Emblem matching provided official branding */}
      <svg
        width={iconWidth}
        height={iconHeight}
        viewBox="0 0 100 95"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{ flexShrink: 0 }}
      >
        <defs>
          <linearGradient id="barGrad" x1="0%" y1="100%" x2="0%" y2="0%">
            <stop offset="0%" stopColor="#38bdf8" />
            <stop offset="100%" stopColor="#7dd3fc" />
          </linearGradient>
          <linearGradient id="arrowGrad" x1="0%" y1="100%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#0284c7" />
            <stop offset="100%" stopColor="#0ea5e9" />
          </linearGradient>
        </defs>

        {/* 4 Ascending Analytics Bars inside the lens */}
        {/* Bar 1 */}
        <rect x="34" y="58" width="6.5" height="15" rx="2.5" fill="url(#barGrad)" />
        {/* Bar 2 */}
        <rect x="43" y="50" width="6.5" height="23" rx="2.5" fill="url(#barGrad)" />
        {/* Bar 3 */}
        <rect x="52" y="42" width="6.5" height="31" rx="2.5" fill="url(#barGrad)" />
        {/* Bar 4 */}
        <rect x="61" y="34" width="6.5" height="39" rx="2.5" fill="url(#barGrad)" />

        {/* Upward Zig-Zag Trend Line with Arrow through the lens */}
        <path
          d="M32 50 L46 37 L56 43 L76 22"
          stroke="#0284c7"
          strokeWidth="4.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* Arrow Head */}
        <path
          d="M67 20 L77 21 L78 31 Z"
          fill="#0284c7"
          stroke="#0284c7"
          strokeWidth="2"
          strokeLinejoin="round"
        />

        {/* Magnifying Glass Outer Rim */}
        <circle
          cx="48"
          cy="42"
          r="28"
          stroke="#0e4f6d"
          strokeWidth="7"
          fill="none"
        />

        {/* Magnifying Glass Angled Handle */}
        <rect
          x="18"
          y="68"
          width="9"
          height="22"
          rx="4.5"
          transform="rotate(42 18 68)"
          fill="#0e4f6d"
        />
      </svg>

      {/* MEDLYTICS Brand Wordmark */}
      {showText && (
        <span
          style={{
            fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
            fontWeight: 900,
            fontStyle: 'italic',
            fontSize: `${Math.max(14, Math.round(size * 0.48))}px`,
            letterSpacing: '1.2px',
            color: textColor,
            lineHeight: 1,
            display: 'inline-block',
          }}
        >
          MEDLYTICS
        </span>
      )}
    </div>
  )
}
