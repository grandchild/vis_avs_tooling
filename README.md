
## Various AVS helper scripts & tools

### Includes
(ordered by relative importance/relevance)

- [`sort_effects.py`](sort_effects.py)

    Parses the AVS source and prints the progress of the new-style API porting effort.
    Detects ported-and-committed as well as work-in-progress effects. Includes a
    "markdown" mode for updating vis_avs#11.

- [`port_effect.py`](port_effect.py)

    Prints out the new-style libavs API version as header, render and UI parts, as far
    as possible. This is the starting point for every new-style API effect-port commit.
    It uses a template and parses `components.json` for each effect's details and
    parameters. Includes, among many things, a generic template for parameter on-change
    callbacks and abbreviated effect name parsing (i.e. passing "DyDistMod" will find
    DynamicDistanceModifier).

- [`components.json`](components.json)

    The definitions of most known AVS effects, their type, identifier and parameter
    definitions. Used by `sort_effects.py` & `port_effect.py`. Generated with
    `print-components-json.ts` from the webvsc project.

- [`find_effect.py`](find_effect.py)

    Finds all effects in a certain directory that use a given effect and assembles
    (i.e. symlinks) them all into a special collection folder. Useful for debugging a
    specific effect, by testing all known usages. Uses fuzzy finding for effect name
    and suggests matches. Works on .webvs files converted from .avs files with
    webvsc-cli. Assumes that for every .webvs file there's a corresponding .avs file
    right next to it. Every linked file in the collection will have its filename
    prefixed by the total number of effects in the preset, so one can spot simple or
    large presets easily.

- [`mkdist.sh`](mkdist.sh)

    Copy all needed and optional DLLs from the Winamp2 directory into a zip archive for
    uploading to the avs.sh server's dev builds directory.

- [`gen-component-headers.sh`](gen-component-headers.sh)

    Script used to create vis_avs@84bc9a8 "Split off effect headers". Uses an extensive
    set of regular expressions to find effect class declarations and put them into
    dedicated header files.

- [`print-components-json.ts`](print-components-json.ts)

    Parses the effects config from the webvsc project and outputs it as pure JSON.

- [`new_comp.sh`](new_comp.sh)

    Generates a set of old-style cpp and header files with an effect-class skeleton.
    Used in the past when reverse-engineering and recreating APEs as builtin.

- [`effect-spec.json`](effect-spec.json)

    Draft of a formal specification for each effect's parameter structure. See
    `effect-spec-spec.{json,yaml}`. A bit outdated.

- [`effect-spec-spec.json`](effect-spec-spec.json)
- [`effect-spec-spec.yaml`](effect-spec-spec.yaml)

    Draft of a meta-spec for the specification of the effects' parameter structure. A
    bit outdated.

- [`effect-spec.py`](effect-spec.py)

    Test script to check the spec against the spec-spec. Unfinished. Only parses and
    re-formats the test spec file.

- [`port_effect_tables.py`](port_effect_tables.py)

    Lists of select options for various effects' parameters. Used by `port_effect.py`.

- [`progress_bar.py`](progress_bar.py)

    Small helper lib to output a progress bar, used by `sort_effects.py`.
