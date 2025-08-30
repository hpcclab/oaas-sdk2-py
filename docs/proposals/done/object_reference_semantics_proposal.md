# Proposal: Object Reference Fields (Identity-based serialization + RPC forwarding)

Scope: Interface-only design. When an OaaS object field holds another OaaS object, the value is stored and transmitted by identity (ObjectMetadata), and using that field yields a proxy whose method calls perform RPCs to the referenced object.

## Goals
- Represent relationships between objects without embedding full state.
- Keep references lightweight and stable across processes/agents.
- Make method calls on referenced objects feel natural (typed, awaitable), while routing over RPC.

## Core Concepts
- Object identity: `ObjectMetadata` (cls_id: str, partition_id: int, object_id: int).
- Reference proxy: a lightweight value that exposes the target service's async methods and holds `metadata`.

## User-Facing Rules
1) Declaring reference fields
- Type a field as another service class (or optional/collections thereof):
  - Single: `child: ChildService | None`
  - List: `children: list[ChildService]`
  - Dict: `index: dict[str, ChildService]`
- Fields remain normal attributes on the class with type annotations.

2) Serialization/Deserialization
- On persist/transport, reference fields are serialized as identity only: `{ cls_id, partition_id, object_id }`.
- On load, reference fields are deserialized as proxies (not full objects). Proxies:
  - Expose the service's annotated async methods.
  - Provide `metadata: ObjectMetadata` property.
  - Do not include target state; method calls execute remotely.

3) Setting reference fields
- You may assign any of:
  - An in-process instance of the target object (e.g., `ChildService`).
  - A reference/proxy to that object.
  - A raw `ObjectMetadata` (or `(cls_id, partition_id, object_id)` tuple).
- Assignment normalizes to a proxy; persisted form is identity.

4) Invoking methods on references
- `await parent.child.do_work(args)` performs an RPC to the child's method.
- Calls use the current SDK configuration (partition, timeouts, etc.).
- In mock/local mode, if the target instance is available in-memory, the call may be served locally (implementation-defined; interface unchanged).

5) Equality and representation
- Proxies compare equal if `(cls_id, partition_id, object_id)` match.
- `str(proxy)` includes `cls_id` and `object_id` for debugging.

## Minimal API Additions (Interfaces)
- Reference helper (optional ergonomic API):
  - `oaas.ref(cls_id: str, object_id: int, partition_id: int = 0) -> T` (returns a proxy of the service type `T`)
- On all objects:
  - `self.metadata: ObjectMetadata` (read-only).
  - `self.as_ref() -> Self` (returns a proxy of `Self`)
- Proxy surface:
  - `proxy.metadata: ObjectMetadata`
  - Service methods as `async def` matching the target class annotations.

## RPC Parameters and Return Values (Pass-by-reference semantics)
Extend identity-based semantics to RPC: when service objects cross a method boundary, they go by identity and surface as proxies on the other side.

- Parameter normalization
  - If a parameter is annotated as an OaaS service type (e.g., `p: Profile`), the client stub accepts any of:
    - In-process instance (`OaasObject`)
  - A proxy of type `T`
    - `ObjectMetadata` or `(cls_id, partition_id, object_id)` tuple, or an equivalent dict
  - Wire format is identity-only: `{ cls_id, partition_id, object_id }`.
  - On the callee, the parameter is presented as a proxy of the annotated type. If a local in-memory instance is available, the runtime may optimize to local dispatch (interface unchanged).

- Return value normalization
  - If a method is annotated to return a service type `T` (or collections thereof), the implementation may return an in-process instance, a proxy, or `ObjectMetadata`; transport serializes identity-only, and the caller receives a proxy of `T`.
  - `None` is preserved.

- Collections and optionals
  - `list[T]`, `dict[K, T]`, `set[T]`, `tuple[...]`, and `Optional[T]` where `T` is a service type map element-wise to identities on the wire and to proxies at the destination.

- Untyped parameters
  - If a parameter lacks a service type annotation but is explicitly a proxy or `ObjectMetadata`, it is normalized as a reference. Passing a plain `OaasObject` without a service type annotation yields `TypeError` to avoid accidental by-value embedding.

- Validation and errors
  - `TypeError` if a provided value cannot be normalized to the annotated service type.
  - `OaasError.NotFound` if the referenced object id does not exist when first used (configurable eager/lazy check).
  - `OaasError.AccessDenied` on permission failures.

- Method-level options (optional)
  - `@oaas.method(validate_refs="lazy" | "eager")` controls whether existence/ACL checks occur at call time or upon first use.
  - Future consideration: `pass_by="ref"` (default) vs `pass_by="value"` for DTO-like non-service models.

## Examples
```python
@oaas.service("Profile", package="example")
class Profile(OaasObject):
    email: str = ""

    @oaas.method()
    async def get_email(self) -> str:
        return self.email

@oaas.service("User", package="example")
class User(OaasObject):
    # Reference to another OaaS object
    profile: Profile | None = None

    @oaas.method()
    async def link_profile(self, p: Profile) -> bool:
        self.profile = p  # accepts instance, becomes a proxy internally
        return True

    @oaas.method()
    async def read_profile_email(self) -> str | None:
        if self.profile is None:
            return None
        return await self.profile.get_email()  # RPC to Profile object
```

Assigning by metadata directly:
```python
meta = ObjectMetadata(cls_id="example.Profile", partition_id=0, object_id=123)
user.profile = meta  # normalized to a proxy
```

Creating refs explicitly:
```python
prof_ref = oaas.ref(cls_id="example.Profile", object_id=123)
user.profile = prof_ref
```

Collections of refs serialize as arrays/maps of identities; accessing items returns proxies.

## Serialization Layer (SDK-wide)
Canonical wire form for any reference (single or inside collections):
```json
{ "cls_id": "<package.Class>", "partition_id": 0, "object_id": 123 }
```

Normalization (to wire):
- Accepts: in-process instance (`OaasObject`), a proxy of a service type, `ObjectMetadata`, `(cls_id, partition_id, object_id)` tuple, or dict with those keys.
- Emits: exactly the metadata dict above.
- Collections (`list`/`dict`/`set`/`tuple`/`Optional`): normalize element-wise.

Materialization (from wire):
- Given metadata, produce a typed proxy of `T` whose methods invoke RPC.
- May optimize to an in-memory instance if available; interface unchanged.

Safety defaults:
- Never serialize full target state through references; proxies are recursion-safe.

## Pydantic Integration

Recommended (Pydantic v2): provide a reusable `Ref[T]` type alias that coerces inputs to proxies of `T` and serializes to identity.

```python
from __future__ import annotations
from typing import Any, TypeVar, Annotated
from pydantic import BaseModel, BeforeValidator, PlainSerializer, ConfigDict

T = TypeVar("T")

def _normalize_to_ref(v: Any):
  # If it's already an OaaS service instance or proxy, keep or convert to proxy
  if isinstance(v, OaasObject):
    # Ensure proxy form for pass-by-identity
    try:
      return v.as_ref()
    except AttributeError:
      return v  # assume it's already a proxy
  # Accept ObjectMetadata
  if isinstance(v, ObjectMetadata):
    return oaas.ref(v.cls_id, v.object_id, v.partition_id)
  # Accept tuple (cls_id, partition_id, object_id)
  if isinstance(v, tuple) and len(v) == 3 and isinstance(v[0], str):
    cls_id, partition_id, object_id = v
    return oaas.ref(cls_id, object_id, partition_id)
  # Accept dict form
  if isinstance(v, dict) and "cls_id" in v and "object_id" in v:
    return oaas.ref(v["cls_id"], v["object_id"], v.get("partition_id", 0))
  raise TypeError(f"Cannot normalize value to a service reference: {v!r}")

def _serialize_ref(v: Any):
  m = v.metadata
  return {"cls_id": m.cls_id, "partition_id": m.partition_id, "object_id": m.object_id}

# Alias applies the normalization/serialization while keeping type hint as the service type T
Ref = Annotated[T, BeforeValidator(_normalize_to_ref), PlainSerializer(_serialize_ref, return_type=dict)]

class UserMsg(BaseModel):
  model_config = ConfigDict(arbitrary_types_allowed=True)
  profile: Ref[Profile] | None = None
  friends: list[Ref[Profile]] = []
  index: dict[str, Ref[Profile]] = {}

# Accepts instance, proxy, metadata dict/tuple; serializes to identity
# m = UserMsg(profile=user.profile)
# m.model_dump() -> {'profile': {'cls_id': 'example.Profile', 'partition_id': 0, 'object_id': 123}, ...}
```


## Validation and Errors (Interface)
- `TypeError` if an assigned value cannot be normalized to a reference of the declared type.
- `OaasError.NotFound` if a method call targets a non-existent object id.
- `OaasError.AccessDenied` on permission failures.
- No cross-object atomic transactions in this proposal.

## Compatibility
- Additive feature; existing fields unaffected.
- Plain data fields (dicts, lists, models) remain embedded as-is.
- Reference fields must be typed with OaaS service classes to opt in.

## Open Questions
- Should assignment validate existence eagerly or lazily (on first use), and can this be configured?
