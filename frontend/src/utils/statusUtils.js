export function statusClass(value) {
  if (!value) return 'unknown'
  const v = String(value).toLowerCase().replace(/[\s_]/g, '-')
  if (v === 'anomalous')  return 'anomalous'
  if (v === 'normal')     return 'normal'
  if (v === 'at-risk' || v === 'at_risk') return 'at-risk'
  if (v === 'breached')   return 'breached'
  if (v === 'on-track' || v === 'on_track') return 'on-track'
  if (v === 'pass')       return 'pass'
  if (v === 'warning')    return 'warning'
  if (v === 'fail')       return 'fail'
  if (v === 'high')       return 'high'
  if (v === 'medium')     return 'medium'
  if (v === 'low')        return 'low'
  return 'unknown'
}
export function fmtLabel(value) {
  if (value == null) return 'Not available'
  return String(value).toLowerCase().replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}
export function fmtNum(value, decimals) {
  if (decimals === undefined) decimals = 4
  if (value == null || value === '') return 'Not available'
  var n = Number(value); if (isNaN(n)) return String(value)
  return n.toFixed(decimals)
}
export function fmtPct(value) {
  if (value == null || value === '') return 'Not available'
  var n = Number(value); if (isNaN(n)) return String(value)
  return n.toFixed(1) + '%'
}
export function fmtBool(value) {
  if (value === true  || value === 1 || value === 'true'  || value === 'True')  return 'Yes'
  if (value === false || value === 0 || value === 'false' || value === 'False') return 'No'
  return 'Not available'
}
export function resolveAnomalyStatus(fullRecord) {
  if (!fullRecord) return null
  if (fullRecord.ML_Is_Anomalous === true)  return 'ANOMALOUS'
  if (fullRecord.ML_Is_Anomalous === false) return 'NORMAL'
  return null
}
