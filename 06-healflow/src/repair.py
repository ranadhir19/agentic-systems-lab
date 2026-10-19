"""Repair memory: validated (failure signature -> repair) pairs.

The key is deliberately model- and workflow-agnostic — it describes the
*failure*, not where it happened:

    ('exception', 'ToolOutage', first?)      -> retry / compensate_abort
    ('postcondition', 'schema'|'data', first?) -> substitute / rollback_recompute

`first` distinguishes the first failure of a step from a recurrence: a
transient outage wants a retry the first time, but if the retry also
fails, the learned response is different. The runtime checks
applicability (e.g. substitution needs a registered alternate tool)
before trusting a memorized repair, and a repair is only recorded after
its postconditions verify — so the memory accumulates *validated*
strategies, never guesses.
"""
from __future__ import annotations

# Predicates about output structure: when one of these fails, the shape of
# the data changed upstream — a schema change, not a value error.
SCHEMA_PREDS = {"schema_ok", "search_ok", "extract_ok"}


class RepairMemory:
    def __init__(self):
        self._table: dict[tuple, tuple[str, dict]] = {}
        self.hits = 0
        self.misses = 0

    @staticmethod
    def key_for(error, failed_preds, first: bool) -> tuple:
        if error is not None:
            return ("exception", type(error).__name__, first)
        fam = ("schema" if any(p in SCHEMA_PREDS for p in failed_preds)
               else "data")
        return ("postcondition", fam, first)

    def lookup(self, key: tuple):
        hit = self._table.get(key)
        if hit is not None:
            self.hits += 1
        else:
            self.misses += 1
        return hit

    def record(self, key: tuple, repair: str, aux: dict | None = None) -> None:
        self._table[key] = (repair, aux or {})

    def __len__(self):
        return len(self._table)
