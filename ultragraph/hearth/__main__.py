"""Hearth REPL: read tears from stdin, print one line per breath.

``python3 -m ultragraph.hearth`` reads lines at the ``tears/write >`` prompt,
feeds each to a :class:`~ultragraph.hearth.loop.Breath`, and prints
``route / heat / offset+appended / collapse / fingerprint``.  Exits on ``exit``
or EOF; ``KeyboardInterrupt`` leaves cleanly too.
"""

from __future__ import annotations

from .loop import Breath

PROMPT = "tears/write > "


def main() -> None:
    """Run the stdin/stdout breath loop until ``exit`` or EOF."""
    breath = Breath()
    while True:
        try:
            line = input(PROMPT)
        except EOFError:
            break
        except KeyboardInterrupt:
            break
        tear = line.rstrip("\n")
        if tear == "exit":
            break
        if tear == "verdict":
            print(f"verdict={breath.verdict()}")
            continue
        if tear.startswith("anchor "):
            text = tear[len("anchor "):]
            idx = breath.anchor(text)
            print(f"anchor={idx}")
            continue
        if tear.startswith("recall "):
            cue = tear[len("recall "):]
            hits = breath.recall(cue)
            print(f"recall {cue!r} -> {len(hits)} hit(s): {', '.join(hits)}")
            continue
        r = breath.feed(tear)
        print(
            f"{r.route.value} / heat={r.heat} / "
            f"{r.offset}+{r.appended} / collapse={r.collapse} / "
            f"mem={len(breath.memnet.log())} / {r.fingerprint}"
        )


if __name__ == "__main__":
    main()