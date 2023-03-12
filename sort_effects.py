from dataclasses import dataclass
from enum import auto
from enum import Enum
import json
import subprocess
import re
import sys

from progress_bar import progress_bar
from progress_bar import PROGRESS_SMOOTH

header_pattern = re.compile(r"e_[a-z][a-z0-9_]+\.h")
old_header_pattern = re.compile(r"c_[a-z_][a-z0-9_]+\.h")

with open("components.json") as f:
    data = json.load(f)


class Params:
    def __init__(self, fields):
        self.params = []
        for name, _ in fields.items():
            self.params.append(name)

    def __str__(self):
        return ",".join([p for p in self.params])

    def __repr__(self):
        return self.__str__()


@dataclass
class Effect:
    name: str
    code: int | str
    group: str
    func: str
    params: Params
    has_enabled: bool


class PortStatus(Enum):
    NEVER = auto()
    NO = auto()
    WIP = auto()
    DONE = auto()

    @staticmethod
    def prefix(status):
        prefixes = {
            PortStatus.NEVER: " ✘ ",
            PortStatus.NO: "   ",
            PortStatus.WIP: "  ▶",
            PortStatus.DONE: " ✔ ",
        }
        return prefixes[status]


def check_ported(name) -> PortStatus:
    if name in [
        "Buffer Blend",
        "FyrewurX",
        "Fluid",
        "AVI Player",
        "Particle System",
        "MIDI Trace",
    ]:
        return PortStatus.NEVER
    cmd = f"rg -il 'name = \"{name.replace(' ', '.?')}\"'"
    search_path = "../vis_avs/avs/vis_avs"
    out = subprocess.run(
        cmd, cwd=search_path, shell=True, capture_output=True
    ).stdout.decode()
    if header_pattern.match(out):
        return PortStatus.DONE
    if old_header_pattern.match(out):
        return PortStatus.WIP
    return PortStatus.NO


def main(output="default"):
    effects = []
    for effect in data:
        code = effect["code"]
        if isinstance(code, int):
            if code > 2**31:
                code -= 2**32
        else:
            code = "".join(chr(c) for c in code if c >= ord(" "))
        effects.append(
            Effect(
                effect["name"],
                code,
                effect["group"],
                effect["func"],
                Params(
                    {
                        k: v
                        for k, v in effect.get("fields", {}).items()
                        if not k.startswith("null")
                        and k not in ["enabled", "new_version"]
                    }
                ),
                "enabled" in effect.get("fields", {}),
            )
        )
    effects.sort(key=lambda e: len(e.params.params))
    total = len(effects)
    ported = 0
    wip = 0
    for effect in effects:
        param_count = len(effect.params.params) or int(effect.has_enabled) or "???"
        has_code = any(["code" in name.lower() for name in effect.params.params])
        port_status = check_ported(effect.name)
        if port_status == PortStatus.WIP:
            wip += 1
        elif port_status == PortStatus.DONE:
            ported += 1
        elif port_status == PortStatus.NEVER:
            total -= 1
        if output == "markdown":
            highlight = "_"
            check = f"[{'x' if port_status == PortStatus.DONE else ' '}]"
            if port_status == PortStatus.NEVER:
                highlight = "~"
                check = ""
            print(
                f" - {check}"
                + f" {highlight}{effect.name}{highlight}"
                + f" ({param_count})"
            )
        else:
            if output == "todo" and port_status in [PortStatus.DONE, PortStatus.NEVER]:
                continue
            print(
                PortStatus.prefix(port_status),
                "</>" if has_code else "   ",
                f"{effect.name: <27} {param_count: ^3}    {effect.code: >5}",
            )
    if output != "markdown":
        print(
            """─────────────────────────────────────────────────────────────────
 ││  └─ codeable                     │         │
 │└─ WIP       number of parameters ─┘         │
 └─ ported                                ID ──┘"""
        )
        progress_bar(ported + wip * 0.5, total, PROGRESS_SMOOTH, 48)
        print()
        print(f"++++++++ {ported} of {total} effects ported, {wip} WIP ++++++++")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["markdown", "todo"]:
        main(output=sys.argv[1])
    else:
        main()
