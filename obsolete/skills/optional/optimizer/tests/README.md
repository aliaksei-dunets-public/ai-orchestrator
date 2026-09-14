# Optimizer Self-Test Fixtures

These fixtures define behavioral expectations for an external agent/eval
harness. The static validator checks that every case has a matching expected
file, but it does not execute an LLM.

For each case, run optimizer in the specified mode and verify that required
findings appear, forbidden behavior does not appear, and the report remains
proportional to the input.

Recommended pass criteria:

- all required root causes detected;
- no invented critical findings;
- no recommendation to remove required safety controls;
- correct reference routing;
- evidence and confidence labels present;
- output stays within the requested mode;
- response compression retains required evidence and validation;
- agent handoffs contain deltas rather than narrative history.
- optimizer default reports contain only important findings, changes, conditional questions, and metrics;
- execution model, scorecard, architecture, and implementation plan appear only in explicitly requested deep output.
- user-facing report language follows explicit instruction or the latest substantive user request, while technical tokens remain unchanged.
