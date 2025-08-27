# Proposal: Accessor Methods (`@oaas.getter`, `@oaas.setter`) – Interface Only

Scope: Introduce simple, explicit decorators to mark read-only and write accessors for persisted fields on OaaS objects. This document defines the user-facing API only (no backend details).

## Goals
- Provide a clear, minimal interface for accessor methods.
- Encourage consistent naming and type-safety for common get/set patterns.
- Keep behavior backward-compatible and purely additive.

## New Decorators

### 1) `@oaas.getter`
Marks a method as a read-only accessor for a persisted field.

Signature (decorator):
- `@oaas.getter(field: str | None = None, *, projection: list[str] | None = None)`

Method contract:
- Async method with no parameters (other than `self`).
- Return type must match the annotated type of the target field (or the projected sub-type when `projection` is used).
- Method body should not perform side effects; it semantically returns the current value of the field.

Example:
```python
@oaas.service("Counter", package="example")
class Counter(OaasObject):
    count: int = 0

    @oaas.getter(field="count")
    async def get_value(self) -> int:
        return self.count
```

Notes:
- `projection` is optional and only for structured fields (e.g., Pydantic models, dict-like). If provided, the method's return annotation should reflect the projected shape.
- If `field` is omitted, it is inferred from the method name (see "Field inference").

### 2) `@oaas.setter`
Marks a method as a write accessor for a persisted field.

Signature (decorator):
- `@oaas.setter(field: str | None = None)`

Method contract:
- Async method with a single parameter (besides `self`): `value`.
- Parameter type must match the annotated type of the target field.
- Returns the updated value (same type as field). If the method annotation is `-> None`, the return value is ignored by callers.
- Method body should only write the field; avoid unrelated side effects.

Example:
```python
@oaas.service("Counter", package="example")
class Counter(OaasObject):
    count: int = 0

    @oaas.setter(field=None)  # inferred from method name: set_value -> value
    async def set_value(self, value: int) -> int:
        self.count = value
        return self.count
```

## Field inference (optional)
If the `field` argument is omitted on the decorator, it is inferred from the method name using the following rules:

- Getter inference:
  - If method name matches `get_<field>` then `<field>` is used.
  - Otherwise, if method name exactly equals a declared annotated field name, that name is used.

- Setter inference:
  - If method name matches `set_<field>` then `<field>` is used.
  - Otherwise, if method name exactly equals a declared annotated field name, that name is used.

Notes:
- Field names are matched as-is (snake_case recommended). No automatic case conversion.
- The inferred field must exist as a type-annotated attribute on the class.
- If multiple rules could apply or no valid field can be resolved, a `TypeError` is raised at decoration time.

## Validation Rules
- Decorators may only reference fields declared on the class with type annotations.
- Getter methods must be zero-argument (besides `self`). Setter methods must accept exactly one argument named `value` (recommended) or a single positional parameter.
- Method type annotations should align with the field types (and projection when used).
- If `field` is omitted, name-based inference must resolve to a valid field per the rules above.
- Accessor methods should not be combined with other operation decorators (e.g., `@oaas.method`).

## Recommended Naming
- Getter: `get_<field>()` or domain-specific read name (e.g., `get_value()`).
- Setter: `set_<field>(value)` or domain-specific write name (e.g., `set_value(value)`).

## Behavior Guarantees (Interface Level)
- Accessors are standard OaaS methods from the caller perspective (awaitable, typed I/O).
- They may be used alongside normal methods within the same service.
- In mock/local mode, behavior follows in-memory state semantics.

## Errors (Interface Level)
- `AttributeError` if `field` is not present on the class.
- `TypeError` if method signature or annotations mismatch the field type (e.g., wrong return type for getter or parameter type for setter).
- `ValueError` for invalid `projection` paths.

## Compatibility
- Additive feature: existing services remain unchanged.
- Services may gradually introduce accessors without breaking callers.

## Quick Reference
- Getter
  - Decorator: `@oaas.getter(field: str | None = None, *, projection: list[str] | None = None)`
  - Method: `async def name(self) -> FieldType`
- Setter
  - Decorator: `@oaas.setter(field: str | None = None)`
  - Method: `async def name(self, value: FieldType) -> FieldType | None`
