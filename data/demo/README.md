# Demonstration catalog

`catalog.json` is a complete, deliberately small `CatalogBundle` with 12
public probe films, 12 public candidate films and the real 12-axis shape. It
contains six disjoint probe pairs, enough to run from session creation to a
ranked pick through the demo API.

The labels are illustrative and the clusters/stopping rule are tuned only to
make the example deterministic and short. This is not a calibrated catalog and
must not be used to infer production quality. It contains no watched history,
ratings, private probe list or production artifact.

Because the demo has only six disjoint pairs and forbids probe reuse,
information gain is not expected to decrease monotonically: a weak remaining
pair can be followed by a stronger one. That small-pool behavior is useful for
exercising the API but is not representative of a full calibrated catalog.

The demo also deliberately uses a strict `entropy_floor_multiple` of `0.1` so
that a six-answer run reaches the `ceiling` path. Values such as `1.29` do not
meet that demo threshold; thresholds quoted in the research/private-deployment
sections of the root README do not apply here. The engine evaluates confidence
before the ceiling when both conditions are checked on the same answer.
