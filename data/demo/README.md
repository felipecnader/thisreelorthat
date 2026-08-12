# Demonstration catalog

`catalog.json` is a complete, deliberately small `CatalogBundle` with 12
public probe films, 12 public candidate films and the real 12-axis shape. It
contains six disjoint probe pairs, enough to run from session creation to a
ranked pick through the demo API.

The labels are illustrative and the clusters/stopping rule are tuned only to
make the example deterministic and short. This is not a calibrated catalog and
must not be used to infer production quality. It contains no watched history,
ratings, private probe list or production artifact.

The 12 candidate and 12 probe embeddings are deterministic synthetic
8-dimensional vectors. They exist only so the public demo can exercise
semantic reranking in a later release without an API call. They are not outputs of
`text-embedding-3-large` and carry no semantic quality claim. Their exact
demo-only generator label is recorded in `embedding_provenance`.

Because the demo has only six disjoint pairs and forbids probe reuse,
information gain is not expected to decrease monotonically: a weak remaining
pair can be followed by a stronger one. That small-pool behavior is useful for
exercising the API but is not representative of a full calibrated catalog.

The demo deliberately uses a low `base_max_rounds` of `6`, so most answer
sequences reach the `ceiling` path. Its `entropy_floor_multiple` of `0.75` is
reachable but demanding for this small pool: some sequences stop by
`confidence`, while most still stop at the round ceiling. Thresholds quoted in
the research/private-deployment sections of the root README do not apply here.
The engine evaluates confidence before the ceiling when both conditions are
checked on the same answer.
