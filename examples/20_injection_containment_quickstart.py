"""Injection-containment quickstart: one injection, blocked by the firewall.

A poisoned search result tells the chain to exfiltrate the customer
database. Undefended, the tool_caller obeys. With the provenance
firewall, the tainted instruction is blocked at first contact.

Run:  python3 examples/20_injection_containment_quickstart.py
"""
from __future__ import annotations

from agentic_systems.injection_containment import Chain
from agentic_systems.injection_containment.defenses import (
    ProvenanceFirewall)


def main() -> None:
    naked = Chain(defenses=[], seed=7).run(
        "exfiltration", carrier_idx=0, hops=4)
    print(f"undefended:  success={naked.success} "
          f"unauthorized_calls={len(naked.unauthorized_calls)}")

    guarded = Chain(defenses=[ProvenanceFirewall("strict")], seed=7).run(
        "exfiltration", carrier_idx=0, hops=4)
    print(f"firewalled:  success={guarded.success} "
          f"unauthorized_calls={len(guarded.unauthorized_calls)} "
          f"blocked={len(guarded.blocked_events)}")

    assert naked.success and naked.unauthorized_calls
    assert not guarded.success and not guarded.unauthorized_calls
    assert guarded.blocked_events
    print("Provenance firewall contained the injection: "
          f"{guarded.blocked_events[0][1]}")


if __name__ == "__main__":
    main()
