# Python Review Reference

Load this reference only after the initial model-led semantic review. It is a
coverage aid, not the primary review method and not an exhaustive definition of
Python quality. Apply sections according to the repository's supported Python
versions, actual framework choices, runtime behavior, and the hypotheses already
formed from the code.

Do not report a rule in isolation. Connect it to a concrete behavior, invariant,
failure mode, security boundary, operational risk, or maintainability cost. Keep
valid model-derived findings even when no section below names them.

## 1. Type Contracts

Check:

- public functions, methods, callbacks, protocols, and data boundaries have
  useful types when the project uses typing;
- annotations match runtime behavior, especially optional returns and raised
  exceptions;
- `Any`, `cast`, `# type: ignore`, and broad unions do not conceal design or
  validation problems;
- collection variance and mutability are intentional (`Sequence` vs `list`,
  `Mapping` vs `dict`);
- protocols or abstract interfaces describe the behavior actually required;
- overloaded functions and generic types remain sound at runtime;
- Pydantic/dataclass/model construction does not bypass validation unexpectedly;
- serialized types remain compatible across API or persistence boundaries.

Do not demand exhaustive typing in an intentionally untyped project. Report
missing types only when they would prevent a demonstrated class of error or
violate project policy.

## 2. Defaults, Mutability, and Object State

Look for:

- mutable default arguments;
- mutable class attributes unintentionally shared by instances;
- dataclass fields missing `default_factory`;
- shallow copies where nested mutation is possible;
- aliases to caller-owned collections that are later mutated;
- cached values that depend on mutable inputs;
- accidental mutation of module globals or singleton state;
- hash/equality behavior inconsistent with mutability;
- frozen dataclasses containing mutable members;
- descriptors or properties with surprising side effects.

## 3. Exceptions and Error Semantics

Check:

- bare `except:` and broad `except Exception` do not swallow cancellation,
  programmer errors, or operational failures;
- caught exceptions are handled, translated, or re-raised intentionally;
- exception chaining uses `raise ... from exc` when translating errors;
- custom exception types preserve actionable context without exposing secrets;
- `finally` blocks and cleanup do not hide the original exception;
- retry logic distinguishes transient from permanent failures;
- APIs return consistent error forms and status codes;
- logging does not duplicate stack traces at multiple layers;
- exception messages do not become unstable test contracts unnecessarily.

## 4. Resource Management

Check that files, sockets, HTTP responses, database sessions, cursors, locks,
transactions, temporary directories, and executors have explicit ownership and
are closed on every path.

Prefer context managers where they express lifecycle accurately. Verify:

- commit/rollback behavior;
- cleanup when constructors or `__enter__` partially fail;
- generator-based context managers re-raise correctly;
- async resources use `async with` and are not leaked on cancellation;
- long-lived client/session reuse is intentional and thread/task safe.

## 5. Async and Concurrency

For async code, inspect:

- blocking filesystem, network, subprocess, database, or CPU-heavy work inside
  the event loop;
- created tasks that are neither awaited nor owned by a lifecycle component;
- cancellation propagation and cleanup;
- broad exception handling that catches `CancelledError` incorrectly for the
  supported Python version;
- unbounded `gather`, task creation, queue growth, or parallel API requests;
- missing timeouts and backpressure;
- shared mutable state across tasks or threads;
- lock scope and deadlock potential;
- use of thread-unsafe clients from executors;
- calling `asyncio.run()` inside an existing event loop;
- loop ownership assumptions in libraries;
- retry storms and duplicated side effects after timeout or cancellation.

For threads/processes, check atomicity assumptions, pool shutdown, picklability,
IPC costs, and whether the GIL changes expected performance.

## 6. Iterators, Generators, and Collections

Check:

- iterators are not consumed twice unexpectedly;
- generators release resources when closed early;
- lazy values do not outlive sessions or transactions they depend on;
- membership and repeated lookup use suitable collection types;
- dictionary/list mutation during iteration is safe;
- ordering assumptions are explicit;
- comprehensions do not conceal exceptions or excessive work;
- large intermediate lists are avoided where streaming is required;
- `itertools.tee` or caching does not create unbounded memory use.

## 7. Functions, Closures, and Decorators

Look for:

- late binding of loop variables in closures;
- decorators that lose metadata because `functools.wraps` is omitted;
- decorator order changing authentication, transactions, caching, or validation;
- default values evaluated at import time unexpectedly;
- partial application binding incorrect arguments;
- callbacks with incompatible sync/async behavior;
- functions with hidden I/O or mutation despite query-like naming.

## 8. Imports and Module Initialization

Check:

- import-time network, database, filesystem, environment, or expensive work;
- circular imports masked by local imports;
- optional dependencies imported unconditionally;
- wildcard imports or re-exports that destabilize public APIs;
- module globals initialized before configuration is available;
- duplicate module instances caused by inconsistent import paths;
- scripts performing work without `if __name__ == "__main__":` when needed;
- plugin registration and side effects are deterministic.

## 9. Data Models, Dataclasses, and Validation

Check:

- dataclass equality, ordering, hashing, slots, and frozen semantics fit usage;
- `__post_init__` validation cannot be bypassed by alternate constructors;
- Pydantic/model validation occurs at the correct trust boundary;
- default values and factories are deterministic;
- aliases, extra fields, strictness, and serialization options preserve
  compatibility;
- ORM model equality and lazy-loading behavior are not mistaken for plain data;
- entity/domain models do not silently accept invalid intermediate states;
- sensitive fields are excluded from repr, logs, and serialization.

## 10. Datetime, Timezones, and Scheduling

Check:

- aware and naive datetimes are not mixed;
- persisted and transmitted timestamps have a documented timezone, normally UTC;
- local-time conversion occurs at a presentation boundary;
- daylight-saving transitions, ambiguous times, and nonexistent times are
  handled where relevant;
- `datetime.now()`/`fromtimestamp()` usage is explicit about timezone;
- tests freeze or inject time rather than relying on wall-clock timing;
- TTL, deadlines, and durations use monotonic clocks where required;
- scheduler behavior after downtime or duplicate execution is defined.

## 11. Numeric and Financial Correctness

When values represent money, prices, quantities, risk, or accounting data:

- avoid binary floating point where exact decimal behavior is required;
- verify rounding mode and rounding boundary;
- preserve currency, unit, scale, and precision in types and schemas;
- check overflow/underflow, NaN, infinities, division by zero, and negative zero;
- ensure aggregation order does not introduce unacceptable error;
- confirm fees, percentages, leverage, and conversions are applied exactly once;
- require tests around thresholds and boundary values.

## 12. I/O, Serialization, and External Boundaries

Check:

- text encoding and newline handling are explicit when relevant;
- JSON/YAML/CSV parsing handles malformed and unexpected shapes;
- unsafe pickle or YAML loaders are not used on untrusted data;
- subprocess arguments avoid shell injection;
- paths are normalized and constrained to intended roots;
- archive extraction prevents path traversal and resource exhaustion;
- HTTP requests define timeout, retries, status handling, and response limits;
- external API pagination and rate limits are handled;
- schema evolution and backward compatibility are tested.

## 13. Database and Transactions

Check:

- query parameterization and identifier handling;
- N+1 queries and accidental full-table scans;
- session/connection lifecycle and transaction ownership;
- atomicity across multiple writes and external side effects;
- isolation and locking assumptions;
- idempotency for retries;
- migration compatibility with rolling deployment;
- indexes supporting new access patterns;
- bulk operations preserving validation and event semantics;
- lazy ORM objects are not accessed after session closure;
- pagination is stable and deterministic.

## 14. Security-Sensitive Python Patterns

Inspect use of:

- `eval`, `exec`, dynamic imports, template evaluation, and expression engines;
- `subprocess` with `shell=True` or interpolated commands;
- `pickle`, `marshal`, unsafe YAML loaders, and custom deserialization hooks;
- temporary files with predictable names or unsafe permissions;
- cryptographic randomness versus `random`;
- path joins based on user-controlled values;
- regexes vulnerable to catastrophic backtracking;
- archive extraction and symbolic links;
- secret values in exceptions, reprs, debug logs, and test fixtures;
- insecure TLS verification or redirects;
- authorization checks located after data access or side effects.

## 15. Performance and Memory

Check only meaningful paths for:

- repeated linear searches where indexed lookup is expected;
- quadratic string/list construction;
- excessive object allocation and copying;
- loading full datasets instead of streaming or pagination;
- unbounded caches and memoization on high-cardinality inputs;
- large closures retaining objects;
- regex compilation in hot loops;
- repeated parsing, serialization, or configuration loading;
- excessive process/thread creation;
- vectorization claims that change semantics or consume excessive memory.

Require measurement before proposing complex optimization when impact is
uncertain.

## 16. Logging and Observability

Check:

- logs use appropriate levels and structured context where supported;
- exceptions are logged once at the layer that can act or report them;
- secrets and personal data are redacted;
- correlation, request, job, or transaction identifiers propagate correctly;
- expected user errors do not create noisy stack traces;
- metrics are bounded in label cardinality;
- health checks reflect real dependencies without causing load;
- background task failures are surfaced rather than lost.

## 17. Pytest and Test Design

Check:

- tests assert behavior, contracts, and important side effects;
- fixtures have the narrowest safe scope and clean up state;
- parametrization covers meaningful equivalence classes and boundaries;
- mocks patch the symbol where it is looked up, not where originally defined;
- mocks preserve realistic interfaces and exception behavior;
- async tests await all work and do not leak tasks;
- time, randomness, UUIDs, environment, filesystem, and network are controlled;
- database tests verify transaction behavior and constraints;
- tests do not depend on order or shared global state;
- `pytest.raises` scopes only the operation expected to fail;
- snapshot tests do not replace semantic assertions;
- coverage increases confidence rather than merely line count.

## 18. Python Review Checklist

Use this checklist selectively:

- [ ] Supported Python version and syntax are compatible.
- [ ] Public/runtime type contracts are coherent.
- [ ] No unintended shared mutable defaults or class state.
- [ ] Exception handling preserves failures and context.
- [ ] Resources close on success, failure, and cancellation.
- [ ] Async paths contain no accidental blocking or orphaned tasks.
- [ ] Concurrency and retries are bounded and idempotent.
- [ ] Iterators/generators have correct lifetime and consumption.
- [ ] Import-time side effects are controlled.
- [ ] Datetime handling is timezone-safe.
- [ ] Numeric precision and rounding match the domain.
- [ ] Serialization and external inputs are validated safely.
- [ ] Database access is transactional, parameterized, and efficient.
- [ ] Logs and errors do not expose sensitive data.
- [ ] Tests are isolated, meaningful, and regression-sensitive.
