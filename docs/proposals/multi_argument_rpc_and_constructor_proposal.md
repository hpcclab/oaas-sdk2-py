# Proposal: Multi-Argument RPC and Constructor Support

## Problem

Current RPC method handling supports either:
- self only
- self + one parameter (deserialized via UnifiedSerializer)
- self + (model, request) i.e., two parameters where the second is the raw InvocationRequest/ObjectInvocationRequest

Constructors mirror the same single-parameter guideline. Users who want multiple independent arguments must wrap them in a single model or dict, which is verbose.

## Goals
- Allow multiple independent parameters for RPC methods and constructors, preserving type hints.
- Maintain backward compatibility and clarity.
- Keep UnifiedSerializer as the single source of truth for element-wise (de)serialization.

## Option: Variadic Packing for RPC and Constructors

### Summary
Support multiple positional/keyword parameters by packing them into a structured envelope at call-time and unpacking them on the callee side. This preserves method signatures while reusing the existing single-payload transport.

### Transport Shape
- Use a JSON object shape with two fields: `args` (list) and `kwargs` (object). Example payload:
  ```json
  {"args": [1, "abc"], "kwargs": {"flag": true}}
  ```
- For return values, keep existing behavior.

### Serialization Rules
- For each parameter in function signature order, apply UnifiedSerializer.convert_value during unpack to coerce JSON to the annotated type.
- For complex types (models, unions, optionals), reuse current conversion logic.
- If any parameter lacks a type hint, deserialize to JSON-native and pass through.

### Constructor Application
- Class-level constructor factories accept multiple parameters and serialize them into the same envelope. Instance-level constructors receive unpacked, typed values.

### Implementation Sketch
- model.py:
  - Extend `_create_caller` to handle `param_count > 3` (or general >=2 non-request parameters):
    - New path `_create_variadic_caller(function, sig)`
    - Deserialize to an envelope dict; iterate parameters to build `bound_args` via `convert_value`.
  - Back-compat: preserve existing 0/1/(model,request) paths.
- simplified/service.py (constructors):
  - Factory captures `*args, **kwargs`, encodes envelope, sets as payload; instance-side wrapper unpacks with the same logic.
- errors.py:
  - Add `ParameterMarshallingError` with details on name, expected type, received value, and index/key.

### Edge Cases
- Default values: if a param is missing, use default; otherwise error.
- Varargs/kwargs only methods: supported by passing through JSON arrays/objects.
- Bytes: base64-encode when using JSON; fall back to pickle based on size/flags.

### Migration
- No breaking changes; single-parameter methods continue to work.
- Add feature flag (e.g., config `enable_variadic_rpc=True`) to gate new behavior initially.

### Testing
- Add tests for:
  - Positional-only, keyword-only, and mixed args
  - Optional/Union coercion per-parameter
  - Constructors with multiple args
  - Error messages on bad arity/type

## Summary
This proposal enables true multi-argument RPC methods and constructors by introducing a simple envelope for transport and typed unpacking using UnifiedSerializer, maintaining backward compatibility and readability.
