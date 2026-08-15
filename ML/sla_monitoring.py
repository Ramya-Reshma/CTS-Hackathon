# ============================================================
# UC10 - Root-Cause Classification Layer (percentages only)
# Adds failure-magnitude classification on top of the existing
# quality_report.json. SLA is a separate downstream pipeline,
# so no SLA data is referenced here.
# Run this in Google Colab AFTER the data quality engine cell.
# ============================================================

import json

with open("outputs/quality_report.json") as f:
    report = json.load(f)

# ============================================================
# Classify each rule by failure magnitude.
# A rule failing on most of the dataset almost always signals a
# systemic/structural defect (schema, casting, upstream mapping) -
# not scattered individual record errors.
# ============================================================
def classify_failure(failure_rate_pct):
    if failure_rate_pct >= 50:
        return "SYSTEMIC"
    elif failure_rate_pct >= 10:
        return "WIDESPREAD"
    elif failure_rate_pct > 0:
        return "ISOLATED"
    else:
        return "NONE"

for r in report["all_rule_results"]:
    r["failure_classification"] = classify_failure(r["failure_rate_pct"])

for r in report["top_failed_rules"]:
    r["failure_classification"] = classify_failure(r["failure_rate_pct"])

systemic = [r for r in report["all_rule_results"] if r["failure_classification"] == "SYSTEMIC"]
widespread = [r for r in report["all_rule_results"] if r["failure_classification"] == "WIDESPREAD"]
isolated = [r for r in report["all_rule_results"] if r["failure_classification"] == "ISOLATED"]
passed = [r for r in report["all_rule_results"] if r["failure_classification"] == "NONE"]

report["classification_summary"] = {
    "systemic_count": len(systemic),
    "widespread_count": len(widespread),
    "isolated_count": len(isolated),
    "passed_count": len(passed),
    "systemic_pct": round(100 * len(systemic) / len(report["all_rule_results"]), 2),
    "widespread_pct": round(100 * len(widespread) / len(report["all_rule_results"]), 2),
    "isolated_pct": round(100 * len(isolated) / len(report["all_rule_results"]), 2),
    "passed_pct": round(100 * len(passed) / len(report["all_rule_results"]), 2),
}

with open("outputs/quality_report.json", "w") as f:
    json.dump(report, f, indent=4)

print(f"Overall Quality Score : {report['overall_quality_score']:.2f}%")
print(f"Overall Risk Level    : {report['overall_risk_level']}")
print()
print("Dimension scores:")
for dim, score in report["dimension_scores"].items():
    print(f"  {dim:<15} {score:.2f}%")
print()
print("Rule classification breakdown:")
cs = report["classification_summary"]
print(f"  SYSTEMIC   : {cs['systemic_count']} rules ({cs['systemic_pct']}%)")
print(f"  WIDESPREAD : {cs['widespread_count']} rules ({cs['widespread_pct']}%)")
print(f"  ISOLATED   : {cs['isolated_count']} rules ({cs['isolated_pct']}%)")
print(f"  PASSED     : {cs['passed_count']} rules ({cs['passed_pct']}%)")
print()
print("Per-rule failure rate + classification:")
for r in sorted(report["all_rule_results"], key=lambda x: x["failure_rate_pct"], reverse=True):
    print(f"  [{r['failure_classification']:<10}] {r['rule_id']} {r['rule_name']:<45} {r['failure_rate_pct']:.2f}%")

print("\nUpdated outputs/quality_report.json with failure_classification + classification_summary.")