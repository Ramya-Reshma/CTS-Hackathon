import React from 'react'

/**
 * Enterprise MEDLYTICS Logo
 * Clean, sophisticated, minimal healthcare intelligence emblem.
 */
export default function MedlyticsLogo({ size = 28, showText = true, textColor = '#ffffff', iconOnly = false }) {
  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '10px', userSelect: 'none' }}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 36 36"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{ flexShrink: 0 }}
      >
        <defs>
          <linearGradient id="medlytics-grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#3b82f6" />
            <stop offset="50%" stopColor="#2563eb" />
            <stop offset="100%" stopColor="#1d4ed8" />
          </linearGradient>
          <linearGradient id="medlytics-accent" x1="0%" y1="100%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#60a5fa" />
            <stop offset="100%" stopColor="#93c5fd" />
          </linearGradient>
        </defs>
        {/* Base rounded container */}
        <rect width="36" height="36" rx="8" fill="url(#medlytics-grad)" />
        {/* Geometric Cross + Intelligence Prism */}
        <path
          d="M18 7V29M7 18H29"
          stroke="#ffffff"
          strokeWidth="3.2"
          strokeLinecap="round"
        />
        {/* Dynamic intelligence diagonal accent nodes */}
        <circle cx="18" cy="18" r="4.5" fill="#ffffff" />
        <circle cx="18" cy="18" r="2.2" fill="#1d4ed8" />
        <circle cx="28" cy="8" r="2" fill="url(#medlytics-accent)" />
        <circle cx="8" cy="28" r="2" fill="url(#medlytics-accent)" />
      </svg>

      {showText && !iconOnly && (
        <span
          style={{
            fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
            fontSize: `${Math.max(16, size * 0.58)}px`,
            fontWeight: 800,
            letterSpacing: '0.8px',
            color: textColor,
            lineHeight: 1,
          }}
        >
          MEDLYTICS
        </span>
      )}
    </div>
  )
}
