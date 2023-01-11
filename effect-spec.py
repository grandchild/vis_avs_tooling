import json
import yaml

with open("effect-spec-spec.yaml") as f:
    spec_spec = yaml.safe_load(f)
with open("effect-spec.json") as f:
    effects = json.load(f)


def parse_effects(effects):
    for name, param_spec in effects.items():
        print(f">>> {name}")
        parse_param_object(param_spec, indent=1)
        print()


def parse_param_object(param_spec, indent=0):
    for name, param_type_spec in param_spec.items():
        iprint(indent, name, end=": ")
        parse_param_type(param_type_spec, indent)


def parse_param_type(param_type_spec, indent):
    if isinstance(param_type_spec, dict):
        type_specs = param_type_spec.items()
    else:
        type_specs = [(param_type_spec, None)]
    for type_, type_config in type_specs:
        print(type_, end="")
        if type_ not in ["BOOL", "NULL", "OBJECT"]:
            print("(", end="")
        if type_ in ["INT", "FLOAT"]:
            print(type_config_string(type_config, ["min", "max"]), end="")
        elif type_ in ["STRING", "BINARY"]:
            print(type_config_string(type_config, ["min_length", "max_length"]), end="")
        elif type_ in ["CHOICE"]:
            print(type_config_string(type_config, ["default"]), end="")
            if "options" not in type_config:
                raise ValueError("Invalid spec, CHOICE type must have 'options' config")
            print(")")
            for option in type_config["options"]:
                iprint(indent + 1, f"'{option}'")
        elif type_ in ["LIST"]:
            print(type_config_string(type_config, ["min_length", "max_length"]), end="")
            if "content_type" not in type_config:
                raise ValueError(
                    "Invalid spec, LIST type must have 'content_type' config"
                )
            print(")")
            iprint(indent + 1, end="")
            parse_param_type(type_config["content_type"], indent + 1)
        elif type_ in ["OBJECT"]:
            print()
            parse_param_object(type_config, indent + 1)

        if type_ not in ["BOOL", "NULL", "CHOICE", "OBJECT", "LIST"]:
            print(")", end="")
        if type_ not in ["CHOICE", "OBJECT", "LIST"]:
            print()


def type_config_string(type_config, keys):
    out = []
    if type_config:
        for key in keys:
            if key in type_config:
                out.append(f"{key} {type_config[key]}")
    else:
        out = [f"no {key}" for key in keys]
    return ", ".join(out)


def iprint(indent, *msg, **kwargs):
    INDENT_WIDTH = 2
    print(" " * indent * INDENT_WIDTH, end="")
    print(*msg, **kwargs)


parse_effects(effects)
