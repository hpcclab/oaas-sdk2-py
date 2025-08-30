# Proposal: Concise Constructor Invocation (No explicit create())

## Problem

Today, users write two steps to initialize a service instance with custom state:

```python
obj = MyService.create()
await obj.init(x, y)
```

This is explicit but verbose for common flows. We want a concise, readable way to “call the constructor” directly on the class to create and initialize the instance in one go, without breaking existing patterns.

## Goals
- Concise: one expression to create + run constructor, returning the instance.
- Familiar: reads like typical object construction while preserving OaaS semantics.
- Safe: no breaking changes; keep instance-level constructor callable.
- Discoverable: supports multiple constructors clearly; good errors on ambiguity.
- Compatible: works in mock and non-mock modes, async/sync constructors, Optional/Union params.

Non-goals
- Changing Python’s __init__ or object allocation semantics for services.
- Auto-invoking constructors silently during `create()`.

## API

We propose adding a class-level entry point that wraps `create()` followed by a constructor call, returning the created instance.

### Class-level constructor invocation (Option A)
Call the constructor method name directly on the class to get a new instance:

```python
# If a constructor named `init` exists
acct = await Account.init(100)
# Equivalent to:
# acct = Account.create(); await acct.init(100)
```

Behavior:
- If accessed on the class, a constructor method returns an async (or sync) factory that:
  1) creates an instance (accepts obj_id/partition_id/local),
  2) invokes the instance constructor with the provided args,
  3) returns the instance.
- If accessed on an instance, the same name remains the normal constructor method (current behavior).
- If multiple constructors exist, calling a specific name is unambiguous: `await Service.setup(...)`, `await Service.bootstrap(...)`.

Optional arguments:
```python
acct = await Account.init(100, obj_id=42, partition_id=7, local=True)
```

Ambiguity:
- If a constructor name isn’t defined, raise a clear error at call time.

## Annotations

`@oaas.constructor()` marks a method as a constructor. Multiple constructors per class are allowed; callers select the constructor by name on the class (e.g., `await Service.bootstrap(...)`). No default selection logic is needed because calls are explicit by name.

## Semantics

- Return: the created instance.
- Async vs sync: mirrors the underlying constructor; factories are async if the constructor is async, sync otherwise.
- Session/config: uses AutoSessionManager under the hood, same as `create()`.
- Parameters: mirror the constructor signature; also accept `obj_id`, `partition_id`, and `local` as keyword-only extras to control identity/placement. If `partition_id` is None, the default from configuration is used.
- Errors: wrap in DecoratorError with clear context (constructor name, args types), consistent with current behavior.
- Accessors and refs: unchanged. This API only shortens the create+construct sequence.

## Examples

Single constructor (async):
```python
@oaas.service("Account", package="ref")
class Account(OaasObject):
    balance: int = 0

    @oaas.constructor(default=True)
    async def init(self, starting: int):
        self.balance = starting

# Concise init
acct = await Account.init(100)
assert await acct.get_balance() == 100
```

Multiple constructors:
```python
@oaas.service("Widget", package="example")
class Widget(OaasObject):
    size: int = 0

    @oaas.constructor()
    async def small(self): self.size = 1

    @oaas.constructor()
    async def large(self): self.size = 10

# Explicit name avoids ambiguity
w = await Widget.large()
```

Controlling identity and locality:
```python
acct = await Account.init(100, obj_id=123, partition_id=7, local=True)
```

Sync constructor (no await):
```python
@oaas.service("Counter", package="ex")
class Counter(OaasObject):
  value: int = 0

  @oaas.constructor()
  def seed(self, start: int):
    self.value = start

# Sync constructor returns directly
c = Counter.seed(10)
assert c.value == 10
```

Distinct constructors (single-parameter):
```python
@oaas.service("Greeter", package="ex")
class Greeter(OaasObject):
  msg: str = ""

  @oaas.constructor()
  async def from_name(self, name: str):
    self.msg = f"Hello, {name}!"

g1 = await Greeter.from_name("Ada")
```

Optional/Union args:
```python
from typing import Optional, Union

@oaas.service("Thing", package="ex")
class Thing(OaasObject):
  note: str = ""

  @oaas.constructor()
  async def make(self, payload: Optional[Union[str, int]] = "ok"):
    self.note = f"payload={payload}"

t = await Thing.make()
t2 = await Thing.make(42)
```

Instance-level constructor still works:
```python
obj = Account.create()
await obj.init(200)
```

Error when calling unknown constructor name:
```python
try:
  await Account.setup(1)  # no @oaas.constructor named 'setup'
except DecoratorError:
  pass
```

## Implementation Sketch

Registration changes (in `simplified/service.py`):
- When processing `@oaas.constructor`, wrap methods in a descriptor `ConstructorInvoker` instead of a plain function.
- Descriptor behavior:
  - `obj is None` (accessed on class): return a factory callable `async def factory(*args, obj_id=None, partition_id=None, local=None, **kwargs)` that:
    - acquires the global AutoSessionManager (`auto = OaasService._get_auto_session_manager()`),
    - resolves `cls_meta` (`cls._oaas_cls_meta`),
    - creates the instance via `auto.create_object(cls_meta, obj_id=obj_id, partition_id=partition_id, local=local)`,
    - invokes the bound instance constructor,
    - returns the instance.
  - `obj is not None` (accessed on instance): return the existing bound method wrapper.

Notes:
- No change to state descriptors, serialization, or ObjectRef.
- Backward compatible: instance-level constructor calls still work; no auto-invoke during `create()`.
- Works seamlessly with mock and real backends via AutoSessionManager.

## Edge Cases & Errors
- No constructors defined → class-level call raises a clear error naming the missing constructor.
- Passing unknown kwargs (like `obj_id`) into the constructor signature → consume in factory only; don’t forward to the method.
- Sync constructors: factories are sync and return instances directly.

## Alternatives Considered
- Overriding `__call__` on the class to mimic `Class(...)` → conflicts with Python instantiation and BaseObject initialization.
- Factory functions (`oaas.instantiate(Class, ...)`) → less discoverable; still useful as internal helper.
- Auto-invoking constructors inside `create()` → surprising, breaks current explicitness.

## Migration & Adoption
- Zero migration required; this is additive.
- Add docs/examples: “Constructors: concise class-level invocation.”
- Add tests covering: class-level call, obj_id/local passing, multiple constructors, default selection.

## Summary
This proposal introduces concise, class-level constructor invocation that returns a fully initialized instance, reducing boilerplate without sacrificing clarity or changing object lifecycle semantics. It’s additive, backward compatible, and easy to implement via a descriptor wrapper during service registration.
