# CC0 - free software.
# To the extent possible under law, all copyright and related or neighboring
# rights to this work are waived.
"""
A fancy progress bar, allowing for sub-character progress in various styles.

Available styles::

    smooth:   |██████████▎         | 53.20%
    vertical: |██████████▂         | 53.20%
    corners:  |██████████▖         | 53.20%
    shaded:   |██████████░         | 53.20%
    ascii:    |##########.         | 53.20%
    wget:     |==========>         | 53.20%
    stick:    |||||||||||\         | 53.20%
    bullet:   |◯◯◯◯◯◯◯◯◯◯◦         | 53.20%
    beep:     |##########·         | 53.20%

Run ``python progress_bar.py`` in a terminal to see a demo.
"""

import os
import math
import sys
from collections import OrderedDict


METERS = OrderedDict(
    [
        ["smooth", " ▏▎▍▌▋▊▉█"],
        ["vertical", " ▁▂▃▄▅▆▇█"],
        ["corners", " ▖▌▛█"],
        ["shaded", " ░▒▓█"],
        ["arrow", " ▶─"],
        ["ascii", " .:|#"],
        ["wget", " >="],
        ["stick", " -\|/-\|"],
        ["bullet", " ◦·●◎◯"],
        ["beep", " · · #"],
    ]
)

(
    PROGRESS_SMOOTH,
    PROGRESS_VERTICAL,
    PROGRESS_CORNERS,
    PROGRESS_SHADED,
    PROGRESS_ARROW,
    PROGRESS_ASCII,
    PROGRESS_WGET,
    PROGRESS_STICK,
    PROGRESS_BULLET,
    PROGRESS_BEEP,
) = METERS.keys()


def progress_bar(progress, total, style=PROGRESS_SMOOTH, width=None):
    """
    Print a progress bar at a certain `progress` of a `total`, spanning the
    whole terminal width unless given a specific width in characters.

    >>> import time
    >>> for i in range(1000):
    ...     progress_bar(i, 1000-1, style=PROGRESS_VERTICAL)
    ...     time.sleep(0.002)  # do some work
    """
    clear_line = "\033[2K\r"
    border_width = 2
    percentage_width = 7
    total_width = width or os.get_terminal_size().columns
    bar_width = total_width - border_width - percentage_width - 1
    fraction = min(1.0, progress / total)
    if -(border_width + percentage_width) < bar_width <= 0:
        print("{: 7.2}".format(fraction))

    try:
        meter = METERS[style]
    except KeyError:
        try:
            if len(style) >= 3:
                meter = style
            else:
                raise ValueError(
                    "Custom meter style too short, must be 3 chars or more"
                )
        except Exception as e:
            raise ValueError(
                "Progress bar: Meter style {!r} is incompatible ({})".format(style, e)
            )

    if sys.platform == "win32":
        clear_line = "\r" + " " * (total_width - 1) + "\r"
        bar_width -= 1  # One less because the CMD cursor is behind the line, not on the last char.
        # Set CMD to UTF-8 with this command:
        # os.system('chcp 65001 > nul')
        # But it doesn't seem to impress python output. :/
        # So we use ASCII-only for Windows:
        meter = METERS["ascii"]

    greater_fraction = math.floor(bar_width * fraction)
    lesser_fraction = (
        math.floor(((bar_width * fraction) % 1) * len(meter)) if len(meter) > 3 else 1
    )
    print(
        "{clear}|{done}{part_done}{todo}|{percentage: >7.2%}".format(
            clear=clear_line,
            done=greater_fraction * meter[-1],
            part_done=meter[lesser_fraction] if fraction < 1.0 else "",
            todo=meter[0] * (bar_width - greater_fraction - 1),
            percentage=fraction,
        ),
        end="",
    )


def progress_bar_clear():
    """Clear the progress bar, but don't go to the next line."""
    clear_line = "\033[2K\r"
    print("{clear}".format(clear=clear_line), end="")


if __name__ == "__main__":
    ## DEMO ##
    import time

    n = 1000
    for s in list(METERS.keys()) + ["->=", "‾`'\"^-~=#o.,_"]:
        print(s if s in METERS.keys() else "custom literal style")
        for i in range(n // 3):
            progress_bar(i, n, style=s)
            time.sleep(0.001)
        print()
        for i in range(round(n * 0.7), n):
            progress_bar(i, n, style=s)
            time.sleep(0.02)
        progress_bar(n, n, style=s)
        print()
