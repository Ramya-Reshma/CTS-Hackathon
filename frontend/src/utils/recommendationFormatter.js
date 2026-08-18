/**
 * recommendationFormatter.js
 *
 * Transforms raw recommendation / fix summary text or arrays into clean,
 * deduplicated, business-action-oriented bullet points, completely omitting
 * any technical analysis, model internals, or pipeline evaluation logic.
 */

// Patterns indicating technical analysis, model internals, or non-business reasoning to exclude
const TECHNICAL_EXCLUSION_PATTERNS = [
  /inspect\s+contributing\s+features/i,
  /contributing\s+features/i,
  /peer\s+context/i,
  /analyze\s+peer\s+context/i,
  /deterministic\s+rules/i,
  /evaluate\s+deterministic\s+rules/i,
  /model\s+confidence/i,
  /review\s+model\s+confidence/i,
  /model-related\s+reasoning/i,
  /feature-level\s+analysis/i,
  /feature\s+importance/i,
  /review\s+feature\s+importance/i,
  /inspect\s+embeddings/i,
  /vector\s+search/i,
  /internal\s+evaluation\s+logic/i,
  /technical\s+validation\s+methodology/i,
  /raw\s+(rag|llm)\s+reasoning/i,
  /llm\s+reasoning/i,
  /analyze\s+llm\s+reasoning/i,
  /isolation\s+forest/i,
  /z-score/i,
  /iqr\s+check/i,
  /multivariate\s+(anomaly|feature|deviation)/i,
  /residual\s+analysis/i,
  /correlation\s+residual/i,
  /why\s+was\s+this\s+flagged/i,
  /technical\s+analysis/i,
  /technical\s+reasoning/i,
  /technical\s+details/i,
  /decision\s+tree/i,
  /f1\s+score/i,
  /confusion\s+matrix/i,
  /active\s+telemetry/i,
  /telemetry\s+signals/i,
  /detector\s+checks/i,
]

// Technical heading prefixes to strip from strings
const HEADING_PREFIXES = [
  /^(technical\s+analysis|technical\s+reasoning|analysis|technical\s+details|root\s+cause\s+analysis|rca\s+reasoning|internal\s+logic)\s*[:\-–—]\s*/i,
  /^(recommended\s+action[s]?|recommendation[s]?|action\s+items?|actionable\s+steps?|fix\s+summary|suggested\s+actions?|operational\s+action[s]?)\s*[:\-–—]\s*/i,
]

/**
 * Check if a text segment is purely technical reasoning that should be excluded
 */
export function isTechnicalAnalysis(text) {
  if (!text || typeof text !== 'string') return true
  const trimmed = text.trim()
  if (trimmed.length < 5) return true
  return TECHNICAL_EXCLUSION_PATTERNS.some(pattern => pattern.test(trimmed))
}

/**
 * Clean a single bullet point string:
 * - Strip numbering, bullets, dashes
 * - Strip heading prefixes
 * - Capitalize first letter
 * - Ensure proper terminal punctuation
 */
export function cleanActionString(str) {
  if (!str || typeof str !== 'string') return ''
  let cleaned = str.trim()

  // Remove markdown bullet or number prefixes: "* ", "- ", "• ", "1. ", "1) ", "[1] "
  cleaned = cleaned.replace(/^([\*\-•\u2022\u2023\u25E6\u2043\u2219]|\d+[\.\)]|\[\d+\])\s*/, '')

  // Remove common heading prefixes like "Recommended Action:", "Action:", etc.
  HEADING_PREFIXES.forEach(prefix => {
    cleaned = cleaned.replace(prefix, '')
  })

  // Strip leading bullet markers again in case prefix was followed by a bullet
  cleaned = cleaned.replace(/^([\*\-•\u2022\u2023\u25E6\u2043\u2219]|\d+[\.\)]|\[\d+\])\s*/, '')
  cleaned = cleaned.trim()

  if (!cleaned || cleaned.length < 5) return ''

  // Capitalize first character
  cleaned = cleaned.charAt(0).toUpperCase() + cleaned.slice(1)

  // Ensure ends with a period if no terminal punctuation exists
  if (!/[.!?]$/.test(cleaned)) {
    cleaned += '.'
  }

  return cleaned
}

/**
 * Normalize string for deduplication (case-insensitive, ignore punctuation & spacing)
 */
function normalizeForDeduplication(str) {
  return str
    .toLowerCase()
    .replace(/[^\w\s]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

/**
 * Extract actionable recommendations from raw text or array.
 * Performs:
 * 1. Filtering out Technical Analysis sections and technical reasoning
 * 2. Splitting paragraphs, numbered lists, bullet points, and action clauses
 * 3. Cleaning and transforming into business-action orientation
 * 4. Deduplication
 * 5. Context-aware fallback if empty
 *
 * @param {string|string[]} rawInput - The raw recommendation text, array, or object
 * @param {object} [context] - Optional record/anomaly context for fallback
 * @returns {string[]} Array of clean, deduplicated, business-action bullet points
 */
export function formatRecommendations(rawInput, context = {}) {
  const actions = []
  const seenNormalized = new Set()

  const addAction = (actionStr) => {
    const cleaned = cleanActionString(actionStr)
    if (!cleaned) return
    if (isTechnicalAnalysis(cleaned)) return

    const normalized = normalizeForDeduplication(cleaned)
    if (normalized.length < 5) return
    if (seenNormalized.has(normalized)) return

    // Also check if an already added item is a near-duplicate or vice versa
    for (const seen of seenNormalized) {
      if (seen.includes(normalized) || normalized.includes(seen)) {
        if (Math.min(seen.length, normalized.length) / Math.max(seen.length, normalized.length) > 0.8) {
          return // Near duplicate
        }
      }
    }

    seenNormalized.add(normalized)
    actions.push(cleaned)
  }

  // Parse raw input into raw lines/chunks
  const rawChunks = []

  if (Array.isArray(rawInput)) {
    rawInput.forEach(item => {
      if (typeof item === 'string') rawChunks.push(item)
      else if (item && typeof item === 'object') {
        if (item.action) rawChunks.push(item.action)
        else if (item.text) rawChunks.push(item.text)
        else if (item.description) rawChunks.push(item.description)
      }
    })
  } else if (typeof rawInput === 'string' && rawInput.trim()) {
    // Check if input contains distinct sections (e.g. "Technical Analysis:" and "Recommended Action:")
    let text = rawInput.trim()

    // If text has "Technical Analysis:" followed by "Recommended Action:", extract the Recommended Action portion
    const recMatch = text.match(/(?:Recommended\s+Actions?|Actionable\s+Steps?|Fix\s+Summary|Action\s+Items?)\s*[:\-–—]\s*([\s\S]+)/i)
    if (recMatch && recMatch[1]) {
      text = recMatch[1]
    } else {
      // If starts with "Technical Analysis:", strip out the technical analysis segment
      const techMatch = text.match(/Technical\s+Analysis\s*[:\-–—][^.]*\.\s*([\s\S]*)/i)
      if (techMatch && techMatch[1]) {
        text = techMatch[1]
      }
    }

    // Split by newlines first
    const lines = text.split(/\r?\n+/)
    lines.forEach(line => {
      if (line.trim()) rawChunks.push(line.trim())
    })
  }

  // Process each raw chunk
  rawChunks.forEach(chunk => {
    // If chunk contains explicit bullets or numbered items, split them
    if (/(?:^|\n)\s*(?:[\*\-•\u2022\u2023\u25E6\u2043\u2219]|\d+[\.\)])\s+/m.test(chunk)) {
      const bulletItems = chunk.split(/(?:^|\n)\s*(?:[\*\-•\u2022\u2023\u25E6\u2043\u2219]|\d+[\.\)])\s+/).filter(Boolean)
      bulletItems.forEach(item => {
        // Also split sentences within bullet if multiple sentences
        const sentences = item.split(/(?<=[.!?])\s+(?=[A-Z])/).filter(Boolean)
        if (sentences.length > 1) {
          sentences.forEach(s => addAction(s))
        } else {
          addAction(item)
        }
      })
    } else {
      // Split by semicolon or sentence boundaries (". ")
      const sentenceItems = chunk.split(/(?:;\s*|(?<=[.!?])\s+(?=[A-Z]))/).filter(Boolean)
      sentenceItems.forEach(sentence => {
        // Check if sentence has comma-separated clauses with mixed technical phrases
        if (sentence.includes(',') && TECHNICAL_EXCLUSION_PATTERNS.some(p => p.test(sentence))) {
          const clauses = sentence.split(/,\s*/).filter(Boolean)
          clauses.forEach(clause => {
            if (!isTechnicalAnalysis(clause)) {
              addAction(clause)
            }
          })
        } else {
          addAction(sentence)
        }
      })
    }
  })

  // If no actionable recommendations were extracted (or input was empty / purely technical),
  // generate standard evidence-grounded business actions based on record context
  if (actions.length === 0) {
    const isAnomalous = context.isAnomalous || context.severity === 'HIGH' || context.severity === 'MEDIUM' || (context.anomaly_type && context.anomaly_type !== 'Normal')
    const isSlaBreached = context.slaStatus === 'BREACHED' || context.slaStatus === 'AT_RISK' || context.sla_breached
    const isDqDefect = context.dqStatus === 'FAIL' || context.dqStatus === 'WARNING' || context.hasDqIssue

    if (isSlaBreached) {
      addAction('Prioritize claims approaching the statutory SLA deadline for immediate adjudication.')
      addAction('Escalate unresolved SLA risks to operational queue supervisors.')
    }

    if (isDqDefect) {
      addAction('Validate the affected claim against the source and master data.')
      addAction('Correct any incorrect field mapping or source value.')
      addAction('Quarantine invalid records when necessary to prevent downstream impact.')
      addAction('Reprocess corrected records.')
    } else if (isAnomalous) {
      addAction('Validate the affected claim against the source and master data.')
      addAction('Correct any incorrect field mapping or source value.')
      addAction('Prioritize claims approaching the SLA deadline.')
      addAction('Quarantine invalid records when necessary.')
      addAction('Reprocess corrected records.')
      addAction('Escalate unresolved high-risk claims with supporting evidence.')
    } else {
      addAction('Routine adjudication approved. No operational hold required.')
      addAction('Proceed with standard claims adjudication workflow.')
    }
  }

  return actions
}
