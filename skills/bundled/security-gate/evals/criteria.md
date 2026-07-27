# Security Gate Evaluation Criteria

## Scoring Dimensions

Each eval scenario is scored on these dimensions (1–5 scale):

### 1. Detection Accuracy (weight: 30%)

- **5**: All planted vulnerabilities detected; no false positives.
- **4**: All critical/high vulnerabilities detected; ≤1 false positive.
- **3**: Most vulnerabilities detected; some false positives or missed medium findings.
- **2**: Missed critical or high vulnerabilities; multiple false positives.
- **1**: Failed to detect obvious vulnerabilities; dominated by false positives.

### 2. Severity Classification (weight: 20%)

- **5**: All findings correctly classified per severity.md criteria.
- **4**: ≤1 misclassification, no severity direction error (high→low or low→high).
- **3**: Minor misclassifications; directional accuracy preserved.
- **2**: Significant misclassification affecting gate decision.
- **1**: Severity assignments are arbitrary or inverted.

### 3. Evidence Quality (weight: 20%)

- **5**: Every finding has exact location, source→sink trace, exploit path, and impact.
- **4**: Minor gaps in evidence; all findings are actionable.
- **3**: Some findings lack specific evidence but are still identifiable.
- **2**: Multiple findings lack evidence; hard to act on.
- **1**: Findings are vague, generic, or unlocated.

### 4. Gate Decision (weight: 15%)

- **5**: Gate decision exactly matches expected outcome and policy.
- **4**: Gate decision correct; minor scope or coverage notation gap.
- **3**: Gate decision correct but with insufficient justification.
- **2**: Gate decision incorrect for the scenario.
- **1**: No gate decision or contradictory decision.

### 5. Report Quality (weight: 15%)

- **5**: Report follows template exactly; all required sections present and complete.
- **4**: Minor formatting or ordering deviations; content complete.
- **3**: Report is usable but missing optional sections or has structural issues.
- **2**: Report is hard to parse or missing required sections.
- **1**: Report is unstructured or missing critical information.

## Composite Score

Weighted sum: `0.30×Detection + 0.20×Severity + 0.20×Evidence + 0.15×Gate + 0.15×Report`

## Pass Thresholds

- **Overall**: composite score ≥ 3.5
- **Detection**: individual score ≥ 3
- **Gate Decision**: individual score ≥ 3

A scenario fails if it does not meet all three thresholds.
