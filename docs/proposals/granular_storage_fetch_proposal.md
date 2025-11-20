# Granular Storage Fetch Proposal

**Status:** Draft  
**Date:** November 2025  
**Target Version:** SDK 3.1 (minor, feature-gated)

## Overview

The latest OaaS control plane exposes *granular storage* APIs: clients can fetch or
persist individual state entries instead of materializing the entire object blob. This
proposal explains how `oaas-sdk2-py` should consume those capabilities so services only
read/write the data they need, lowering latency and bandwidth while keeping backward
compatibility with older runtimes.

Scope:

- Extend the Rust bridge (`oprc-py`) with entry-level operations.
- Teach the Python session/state layers to lazy-load and commit per-entry updates.
- Update accessors, triggers, and ObjectRef proxies to exploit partial fetches.
- Fail fast when the connected server lacks granular support so operators know to
  upgrade their control plane.

## Motivation

1. **Performance:** Large objects currently require full serialization on every read or
   write. Fetching just the touched field avoids multi-KB payloads for single-value
   operations.
2. **Consistency:** Granular APIs surface per-entry versions, enabling optimistic
   concurrency without re-reading the entire object.
3. **UX:** Accessors can act like true property getters/setters—no surprise full loads.
4. **Cost:** Less bandwidth and lower storage write amplification translate to cheaper
   operations on hosted OaaS clusters.

## High-Level Design

### Capability Detection

- Introduce `ServerFeatures` structure returned by the runtime (via `oaas.get_server_info`
  or a dedicated RPC). It flags `granular_storage=true` when the backing ODGM build
  exposes the new API.
- Python requires this capability; if the runtime reports `granular_storage=false` the
  SDK raises a descriptive error instructing the operator to upgrade the server build.

### Rust Bridge (oprc-py)

New methods on `DataManager` (sync + async variants):

| Method | Purpose |
| --- | --- |
| `get_entry(cls_id, partition_id, object_id_str, key: &str)` | Fetch a single slot. |
| `get_entries(cls_id, partition_id, object_id_str, keys: &[String])` | Batch fetch. |
| `set_entries(cls_id, partition_id, object_id_str, values: HashMap<String, Vec<u8>>, expected_version: Option<u64>)` | Batch write with CAS. |
| `list_entries(...) -> EntryIterator` | Iterate over populated slots. |
| `delete_entries(...)` | Remove specific slots without touching others. |

Implementation notes:

- Continue to support `get_obj/set_obj` for compatibility.
- Share serialization helpers so both flows reuse `ObjectData` conversions.
- Emit feature flag to Python layer after initialization.

### Python Session & StateDescriptor

- `Session` stores a per-object cache: `{key -> bytes | None}` plus the current
  `version`. Missing keys trigger lazy fetches via `get_entry()` when granular mode is on.
- `StateDescriptor.__get__` checks `_loaded_fields`; if absent it attempts to fetch only
  that key. If granular storage is unavailable, attribute access raises an
  `UnsupportedFeatureError`.
- Commits accumulate dirty keys and call `set_entries()`; running without granular
  support is no longer permitted.
- Accessors (`@oaas.getter/@oaas.setter`) call the same descriptor pathways, so they
  automatically benefit.

### ObjectRef Enhancements

- Provide `await ref_obj.fetch_entry("field_name")` as a lightweight RPC for remote
  callers that only want one field.
- Extend serialization metadata to carry entry versions so advanced users can supply an
  `expected_version` for CAS semantics.

### Trigger/Event Handling

- When granular mode is available, the handler emits change events with the exact keys
  touched. Existing consumers keep receiving full-object events, but new agents can opt in
  to per-entry payloads (future work; out of scope if server support is partial).

### Feature Enforcement

1. Probe server features at startup.
2. If `granular_storage` is false, immediately raise `UnsupportedFeatureError` so the
  operator upgrades the runtime before proceeding.
3. Accessors and state descriptors assume granular support is present, simplifying
  their code paths.

## Implementation Plan

### Phase 0 – Design & Tooling
- Capture the definitive ODGM proto / API for entry-level calls.
- Add feature-flag plumbing between server and SDK (extend `ServerInfo`).

### Phase 1 – Rust Layer
- Implement the new `DataManager` methods and expose them via PyO3.
- Update `PyDataManager` struct in `oprc_py.pyi` so type checkers know about the extras.
- Provide unit tests (Rust + Python) covering single-entry and batch operations.

### Phase 2 – Python Session Kernel
- Add feature detection and per-object caches (`_entry_cache: dict[str, Optional[bytes]]`).
- Update `get_data`, `set_data`, `commit`, and `fetch` in both `BaseObject` and
  `OaasObject` to branch on feature support.
- Introduce dirty-key tracking so commits can submit only touched entries.
- Ensure delete flows (`delete_object`, `del_obj`) work with partial versions (either
  send a tombstone entry list or call the old API depending on capability).

### Phase 3 – Accessors & ObjectRef
- Modify `StateDescriptor` to call `session.get_entry(key)` instead of force-fetching
  entire objects.
- Update `references.ObjectRef` accessors to call the new helper before hitting RPC.
- Provide an ergonomic API for remote projections (e.g., `ObjectRef.project("field")`).

### Phase 4 – Documentation & Examples
- Add a section to `docs/tutorial.md` describing lazy field loads and the benefits.
- Provide a sample in `examples/helloworld` demonstrating a large object where only a
  single field is read.
- Document the feature flag requirement and failure mode in `docs/reference.md`.

### Phase 5 – QA & Rollout
- Extend mock mode (`LocalDataManager`) so tests can simulate granular storage without a
  real server.
- Add regression tests ensuring the SDK raises `UnsupportedFeatureError` when the flag
  is off.
- Gate the new logic behind an environment variable (`OAAS_FORCE_GRANULAR=1`) during the
  beta so it can be toggled quickly.

## Out-of-Scope / Future Work

- Per-entry event payload delivery (requires server-side agent changes) – to be handled
  after baseline granular storage lands.
- Schema-aware projections (e.g., nested dict keys) – keep scope limited to descriptor
  keys for the initial release.
- Cross-object transactions using per-entry CAS – depends on broader transaction support.

## Risks & Mitigations

| Risk | Mitigation |
| --- | --- |
| Server lacks the feature | Runtime feature detection raises `UnsupportedFeatureError` with guidance to upgrade the control plane. |
| Increased code complexity in session layer | Keep caching helpers narrow and add instrumentation to ensure single-path code stays maintainable. |
| Partial fetch may expose uninitialized descriptors | Initialize caches with sentinels and raise meaningful errors when a field truly does not exist. |
| CAS failures causing user confusion | Document the optimistic concurrency model and expose conflict exceptions with actionable context. |

## Success Metrics

- Accessor reads on a large object (100+ fields) should avoid full `get_obj` calls when
  the server supports granular storage (verified via instrumentation or mocks).
- Regression suite covers both the granular happy path and the unsupported-server error
  path.
- Documentation clearly communicates how to opt in/out and what guarantees exist.

---

*Prepared for review by the OaaS SDK maintainers.*
