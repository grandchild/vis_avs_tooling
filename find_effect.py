from glob import glob
import json
from pathlib import Path
import sys
from pprint import pprint

from thefuzz import fuzz

PRESETS_DIR = Path("/home/jakob/dev/avs/presets/")
LIB_DIRS = [
    PRESETS_DIR / "library_jakob",
    PRESETS_DIR / "library_visbot",
    PRESETS_DIR / "library_tuggummi",
]
TMP_COLLECTION = PRESETS_DIR / "!tmp_collection"
COMPONENTS_DEF = Path("/home/jakob/dev/avs/vis_avs/components.json")


def main():
    if len(sys.argv) < 2:
        sys.exit("Missing effect name")

    effect_name = " ".join(sys.argv[1:])
    check_effect_name(effect_name)
    reset_collection()
    presets_with_size = find_presets_with_effect(effect_name)
    for preset, length in presets_with_size:
        if link_into_collection(preset, length):
            ...
            print(preset)
    print(len(presets_with_size))


def check_effect_name(effect_name):
    possible_effect_names = [e["name"] for e in json.loads(COMPONENTS_DEF.read_text())]
    if effect_name not in possible_effect_names:
        did_you_mean: list[str] = []
        for e in possible_effect_names:
            if fuzz.ratio(e, effect_name) > 50:
                did_you_mean.append(e)
        error_str = f"Error effect '{effect_name}' not found."
        if did_you_mean:
            error_str += f" Did you mean:\n"
            for e in did_you_mean:
                error_str += f"    {e}\n"
        sys.exit(error_str)


def reset_collection():
    TMP_COLLECTION.mkdir(exist_ok=True)
    for f in TMP_COLLECTION.iterdir():
        f.unlink()


def search_effect_and_count_components(
    effect, components: list[dict]
) -> tuple[bool, int]:
    component_count = 0
    has_effect = False
    for component in components:
        component_count += 1
        type_ = component.get("type", "")
        if effect in type_:
            # pprint({k: v for k, v in component.items() if k != "code"})
            has_effect = True
        elif type_ == "Effect List":
            effectlist_has_effect, count = search_effect_and_count_components(
                effect, component.get("components", [])
            )
            has_effect |= effectlist_has_effect
            component_count += count
    return (has_effect, component_count)


def find_presets_with_effect(effect_name) -> list[tuple[Path, int]]:
    _effect_name = effect_name.replace(" ", "")
    preset_files_with_length = []
    for library in LIB_DIRS:
        for f in glob("*/*.webvs", root_dir=library, recursive=True):
            preset = json.loads((library / f).read_text())
            components = preset.get("components", {})
            file_has_effect, preset_size = search_effect_and_count_components(
                _effect_name, components
            )
            if file_has_effect:
                avs_file = library / f.replace(".webvs", ".avs")
                preset_files_with_length.append((avs_file, preset_size))
    return preset_files_with_length


def link_into_collection(preset_file, component_count) -> bool:
    try:
        link = TMP_COLLECTION / f"{component_count:0>3}__{preset_file.name}"
        link.symlink_to(preset_file)
    except FileExistsError:
        return False
    else:
        return True


if __name__ == "__main__":
    main()
