# ODGM Architectural Updates Proposal

**Status:** Draft  
**Date:** November 2025  
**Target Version:** SDK 3.0 (Breaking)

## Overview

This proposal outlines the integration of three major ODGM platform changes into oaas-sdk2-py:

1. **String-Based Object Identifiers** - Human-readable object IDs only (breaking change)
2. **Granular Per-Entry Storage** - Fine-grained state persistence replacing blob serialization
3. **V2 Event Pipeline** - Per-entry change notifications with Create/Update/Delete semantics

## Motivation

The ODGM platform has evolved to support cloud-native patterns, improved debugging, and precise event handling. The SDK must adopt these changes to:

- Enable human-readable object references (e.g., "user-123", "session-abc")
- Reduce write amplification through partial updates
- Provide fine-grained event triggers at the field level
- Simplify the API surface by removing numeric ID complexity

## High-Level Design

### 1. String-Based Object Identifiers (Breaking Change)

**Rust Layer (oprc-py):**
- Replace numeric `object_id: u64` with `object_id_str: String` in all types
- Implement normalization: lowercase ASCII, charset `[a-z0-9._:-]+`, max 160 chars
- Update `ObjectMetadata`, `InvocationRequest`, `ObjectInvocationRequest` to use string IDs only
- Remove TSID generation logic
- Update Zenoh key expressions for agents to embed normalized string IDs

**Python Layer:**
- Change `object_id` type from `int` to `str` across all APIs
- Update `Session.create_object()`, `load_object()`, `delete_object()` to require string IDs
- Remove TSID auto-generation; require explicit ID or generate UUID/ULID-based strings
- Add client-side validation for ID format before Rust normalization
- Update `OaasObject.object_id` property to return `str` only

**API Changes:**
```python
# String IDs required
obj = MyService.create(obj_id="user-123")
loaded = MyService.load(obj_id="user-123")

# Auto-generate if not provided (UUID-based)
obj = MyService.create()  # generates: "obj-<uuid>"

# Numeric-looking strings are allowed
obj = MyService.create(obj_id="12345")  # stored as string "12345"
```

### 2. Granular Per-Entry Storage

**Rust Layer (oprc-py):**
- Expose entry-level operations via `DataManager`:
  - `get_entry(cls_id, partition_id, object_id_str, key: str) -> Optional[bytes]`
  - `set_entry(..., key: str, val: bytes)`
  - `batch_set_entries(..., values: Dict[str, bytes], expected_version: Optional[int]) -> int`
  - `list_entries(...) -> EntryListResult`
  - `get_metadata()`, `set_metadata()`, `delete_entry()`
- Remove legacy blob operations (`get_obj/set_obj` only used for reconstruction if needed)
- Support CAS (Compare-And-Swap) via version checking in batch operations
- All object_id parameters are now string type

**Python Layer:**
- Update `StateDescriptor` to accumulate per-field changes in memory
- Replace full-object commits with `batch_set_entries()` calls (only granular storage)
- Track `expected_version` on objects for optimistic concurrency
- Remove `get_data/set_data` with numeric indices; use field name keys directly
- Add lazy loading: fetch individual entries on first access
- All internal storage uses string keys (field names)

**Storage Model:**
```python
# StateDescriptor now writes per-entry
obj.name = "Alice"      # Accumulates: {"name": <bytes>}
obj.email = "a@ex.com"  # Accumulates: {"email": <bytes>}
obj.commit()            # Calls batch_set_entries({...}, expected_version=N)
                        # Returns new version N+1
```

### 3. V2 Event Pipeline

**Rust Layer (oprc-py):**
- Extend `PyObjectEvent.data_trigger` to include `data_trigger_str: HashMap<String, DataTrigger>`
- Add `manage_data_trigger_str()` method or make `manage_data_trigger()` polymorphic
- Expose optional V2 metrics/broadcast for testing (if available from server)

**Python Layer:**
- Update `manage_trigger()` to accept `source: Union[int, str]` (field key)
- Route string keys to `data_trigger_str` map in event config
- Document Create/Update/Delete semantics for per-entry changes
- Update tests to verify action classification (e.g., Create on first write, Update on subsequent)

**Event Semantics:**
```python
# Trigger on field name (string key only)
obj.trigger(source="email", target_fn=notify, event_type=DataTriggerType.OnUpdate)
obj.trigger(source="count", target_fn=handler, event_type=DataTriggerType.OnCreate)
```

## Implementation Phases

### Phase 1: Rust PyO3 Bindings (oprc-py)
- [ ] Replace `object_id: u64` with `object_id_str: String` in all types
- [ ] Implement string ID normalization logic
- [ ] Update `ObjectMetadata`, `InvocationRequest`, `ObjectInvocationRequest` to use string IDs
- [ ] Implement entry-level DataManager methods (async + sync) with string object_id
- [ ] Update `PyObjectEvent` to use only string-key triggers (remove numeric map)
- [ ] Remove TSID dependencies
- [ ] Export new types in `lib.rs`

**Dependencies:** Updated `oprc_pb` protobuf definitions and `oprc_invoke` with string IDs and entry APIs

### Phase 2: Python Simplified API (Breaking Changes)
- [ ] Change `object_id` from `int` to `str` in `session.py`, `objects.py`
- [ ] Remove TSID generation; add UUID/ULID-based string ID generation
- [ ] Update `StateDescriptor` to use field names as keys (string-based)
- [ ] Replace blob storage with entry batching exclusively
- [ ] Add CAS version tracking to `OaasObject`
- [ ] Update `manage_trigger()` to accept only string keys
- [ ] Update agent key construction in `engine.py` for string IDs
- [ ] Remove numeric index-based storage (`_state: dict[int, bytes]` → `dict[str, bytes]`)

### Phase 3: Testing & Documentation
- [ ] Add unit tests for string ID normalization and validation
- [ ] Test entry-level storage with CAS success/failure scenarios
- [ ] Test V2 event Create/Update/Delete classification with string keys
- [ ] Update all examples (helloworld, device) to use string IDs
- [ ] Update README with new string ID patterns
- [ ] Document breaking changes and migration path in reference docs

### Phase 4: Migration Support
- [ ] Provide migration script or guidance for converting numeric IDs to strings
- [ ] Document recommended string ID patterns (e.g., "user-{uuid}", "{type}-{id}")
- [ ] Create examples showing ID generation strategies
- [ ] Update all tests to use string IDs

## API Compatibility

**Breaking Changes (SDK 3.0):**
- `object_id` changes from `int` to `str` everywhere
- No automatic TSID generation; explicit ID required or UUID-based default
- Numeric index-based storage (`get_data(42)`) removed; use field names
- Blob storage APIs (`set_obj` with full object) removed
- Event triggers require string keys only (no numeric key support)
- All existing code using numeric IDs must migrate

**New Capabilities:**
- Human-readable object identifiers
- Per-entry reads/writes with CAS
- Fine-grained event triggers on individual fields
- Simplified API surface (no dual-mode complexity)

## Testing Strategy

**Rust Layer:**
- Unit tests for `ObjectIdentity` normalization edge cases
- PyO3 binding tests for entry APIs (round-trip from Python)
- Event config tests with both numeric and string keys

**Python Layer:**
- Integration tests with string IDs end-to-end (create → update → load → delete)
- StateDescriptor tests verifying per-entry writes with field name keys
- CAS conflict resolution tests (version mismatch scenarios)
- V2 event tests asserting Create/Update/Delete on string keys only
- Agent startup with string ID object instances
- ID generation tests (UUID-based, custom patterns)

**Migration:**
- All existing tests must be updated to use string IDs
- No regression testing needed for numeric IDs (removed)

## Performance Considerations

**Benefits:**
- Reduced write amplification: only changed fields persist
- Lower memory footprint: lazy load individual entries
- Faster event processing: per-entry granularity avoids full-object diffs
- Human-readable debugging and logging
- Simpler API (no dual-mode complexity)

**Tradeoffs:**
- String IDs add ~8.6 ns overhead per operation (negligible)
- Slightly larger storage overhead (strings vs u64)
- Entry-level storage may increase read latency for full-object reconstruction
- Breaking change requires migration effort

**Benchmarks:**
- Target: entry batch operations < 1ms for typical object sizes (< 100 entries)
- V2 event overhead: < 500 ns per mutation (as per ODGM benchmarks)

## Migration Path

**For Existing Applications (Breaking):**
1. **SDK 3.0 upgrade is breaking** - requires code changes
2. Convert all numeric object IDs to strings:
   ```python
   # Before (SDK 2.x)
   obj = MyService.create(obj_id=12345)
   
   # After (SDK 3.0)
   obj = MyService.create(obj_id="12345")  # or better: "myservice-12345"
   ```
3. Update storage access from numeric indices to field names:
   ```python
   # Before: obj.get_data(0), obj.set_data(0, bytes)
   # After: use typed attributes (obj.name = "value") or explicit field keys
   ```
4. Update event triggers to use string keys (field names)
5. Replace TSID generation with UUID/ULID-based string IDs

**Recommended ID Patterns:**
- `"user-{uuid}"` - User-facing entities
- `"session-{ulid}"` - Time-sortable IDs
- `"{type}-{natural-key}"` - Domain identifiers (e.g., "order-2024-001")
- Avoid: pure UUIDs without context (hard to debug)

**For New Applications:**
- Use descriptive string IDs from the start
- Use typed attributes on `OaasObject` subclasses (automatic field-based storage)
- Configure triggers at field granularity

## Open Questions

1. Default ID generation strategy when `obj_id` not provided?
   - **Recommendation:** UUID4-based with prefix (e.g., "obj-{uuid4}"); allow customization via config

2. Should we validate string ID format in Python before Rust normalization?
   - **Recommendation:** Basic validation (length, charset) in Python for fast-fail UX; Rust does authoritative normalization

3. How to handle string ID length limits in different ODGM deployments?
   - **Recommendation:** Expose configurable max length via SDK config (default 160)

4. Provide migration tooling for numeric → string ID conversion?
   - **Recommendation:** Document patterns + provide example script; full automation difficult due to semantic choices

## Related Proposals

- Accessor Method Proposal (done) - getter/setter semantics complement per-entry storage
- Object Reference Semantics Proposal (done) - identity-based proxies work with both ID types
- Multi-Argument RPC Proposal (pending) - orthogonal but may influence entry serialization format

## Success Criteria

- ✅ String IDs work end-to-end in all example services
- ✅ Per-entry storage reduces commit payload size by >50% for partial updates (benchmark)
- ✅ V2 event tests pass with Create/Update/Delete assertions on string keys
- ✅ All tests migrated to string IDs and passing
- ✅ Documentation includes comprehensive migration guide
- ✅ At least 3 recommended ID generation patterns documented with examples

## Timeline

- **Week 1-2:** Phase 1 (Rust bindings with string-only IDs) + proto/invoke layer coordination
- **Week 3:** Phase 2 (Python breaking changes)
- **Week 4:** Phase 3 (Migrate all tests and examples to string IDs)
- **Week 5:** Phase 4 (Migration guide, docs, and final testing)
- **Target Release:** SDK 3.0.0 (major version bump due to breaking changes)

## References

- ODGM Technical Overview (November 2025)
- `oprc_pb` protobuf definitions
- `oprc_invoke` proxy implementation
- Existing proposals in `/docs/proposals/done/`
