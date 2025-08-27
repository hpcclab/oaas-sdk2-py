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
  - `oaas.ref(cls_id: str, object_id: int, partition_id: int = 0) -> ObjectRef[T]`
- On all objects:
  - `self.metadata: ObjectMetadata` (read-only).
  - `self.as_ref() -> ObjectRef[Self]`
- Proxy surface:
  - `proxy.metadata: ObjectMetadata`
  - Service methods as `async def` matching the target class annotations.

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
- Should proxies be strongly typed (generic `ObjectRef[T]`) in the public API or duck-typed per service methods?
- Should assignment validate existence eagerly or lazily (on first use), and can this be configured?
- How should refs interact with new `@oaas.getter/@oaas.setter` accessors (e.g., `@getter(field="profile", projection=[...])`)?
