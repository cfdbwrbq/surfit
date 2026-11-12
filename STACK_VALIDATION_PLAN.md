# Stack validation gate

## Goal

A solved `SurfaceStack` already reports crossings, thickness and coverage
numbers.  The next step is an explicit pass/fail gate for automation:

```python
stack.validate(
    max_crossings=0,
    min_thickness=1.0,
    min_coverage=0.9,
    strict=True,
)
```

The gate is a policy check over the existing report.  It does not change the
solver and does not invent a second interpretation of the surfaces.

## API

`SurfaceStack.validate(max_crossings=0, min_thickness=None,
min_coverage=None, strict=False)`

Returns:

```python
{
    "ok": bool,
    "violations": [
        {"code": "crossings", "value": 12, "limit": 0, "message": "..."},
        {"code": "thickness", "layer": "top", "value": 0.2, "limit": 1.0},
        {"code": "coverage", "layer": "top", "value": 0.7, "limit": 0.9},
    ],
    "report": {...},
    "thresholds": {...},
}
```

- `max_crossings` is a non-negative integer;
- `min_thickness` is checked against every non-final layer's finite minimum
  thickness; a layer with no overlap is a violation when the threshold is set;
- `min_coverage` is checked against `defined / total` for every layer;
- `strict=True` raises `StackValidationError` carrying the same result.

## Design rules

- no silent pass: a bad threshold or missing solve raises;
- no provider-specific semantics in the gate;
- one report round trip, then pure checks;
- the exception is a `ValueError` subclass so existing callers keep working;
- loaded memory-mapped stacks are validated through the same path.

## Tests

- healthy stack passes, `strict=True` does not raise;
- crossing stack fails with a `crossings` violation and raises in strict mode;
- minimum-thickness violation is reported per layer;
- invalid thresholds raise `ValueError`;
- coverage appears in the report and is checked.

## Non-goals

- repairing crossings automatically;
- fitting thresholds from data;
- 3D volume checks;
- a second solver.
