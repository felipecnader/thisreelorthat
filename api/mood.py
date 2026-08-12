"""Provider boundary for turning free text into engine-ready mood data.

Providers own credentials, retries and caching. The numerical engine receives
only validated components and vectors; it never sees a key, global cache or
filesystem path.
"""

from __future__ import annotations

from typing import Protocol, Sequence

import numpy as np

from engine import MoodComponent, PreparedMood


class MoodProvider(Protocol):
    def decompose(self, text: str) -> Sequence[MoodComponent]: ...


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> Sequence[float]: ...


def prepare_mood(
    text: str,
    *,
    mood_provider: MoodProvider,
    embedding_provider: EmbeddingProvider,
) -> PreparedMood:
    components = tuple(mood_provider.decompose(text))
    vectors = np.asarray([
        embedding_provider.embed(str(component.text))
        for component in components if component.route == "embedding"
    ], dtype=float)
    if not len(vectors):
        vectors = np.empty((0, 0), dtype=float)
    else:
        vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    return PreparedMood(text=text, components=components, embedding_vectors=vectors)


# Reference prompt policy for provider implementations. The comments preserve
# the production failures that motivated each rule; providers may express the
# schema differently but must keep these semantics.
MOOD_ROUTING_RULES = """
Route each independent requirement as axis, embedding, genre, metadata, or
unrepresentable.

General rule: a term about the world inside the film is embedding or genre; a
term about how the film was made or behaves is axis or metadata.

- classic_contemporary means filmmaking grammar and production era, never the
  era portrayed. Case: “épico histórico” became epic+classic and surfaced
  Metropolis (1927).
- Diegetic world, subject, setting and event terms use embedding or genre.
  Case: the same historical-epic failure above.
- Never define an embedding by negation; state the positive desired property.
  Case: “em vez de gore ou sustos” described Stalker and Picnic at Hanging
  Rock surprisingly well.
- Preserve the request's cultural register. Case: Brazilian “besteirol” became
  “slapstick” and surfaced Chaplin, Modern Times and PlayTime.
- Properties absent from axes, synopsis and factual metadata are
  unrepresentable and must be ignored with a warning. Case: visual beauty in
  “terror lento e bonito”.
""".strip()
