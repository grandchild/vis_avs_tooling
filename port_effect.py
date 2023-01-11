from itertools import zip_longest
import json
import re
import sys
from typing import cast
from typing import Optional
from typing import Sequence

from port_effect_tables import tables


def split_camel(string: str) -> list[str]:
    return re.findall(r"(^[a-z][a-z0-9+/-]*|[A-Z]+[a-z0-9+/-]*)", string)


def camel_to_snake(string: str) -> str:
    return "_".join(part.lower() for part in split_camel(string))


class Field:
    c_macros = {
        "List": "std::vector<{subconfig}> {fname};",
        "Bool": "bool {fname} = false;",
        "Uint": "int64_t {fname} = 0;",
        "Int": "int64_t {fname} = 0;",
        "Float": "double {fname} = 0.0;",
        "Color": "uint64_t {fname} = 0xffffff;",
        "SizeString": "std::string {fname};",
        "NtString": "std::string {fname};",
        "Select": "int64_t {fname} = 0;",
        "ColorList": "std::vector<{classname}_Color_Config> {fname};",
        "Int_array": "std::vector<int64_t> {fname};",
        "Float_array": "std::vector<double> {fname};",
        "Color_array": "std::vector<uint64_t> {fname};",
        "_invalid": "void* {fname};",
    }
    c_macros_code = [
        'std::string init = "";',
        'std::string frame = "";',
        'std::string beat = "";',
        'std::string point = "";',
    ]
    p_macros = {
        "Uint": 'P_IRANGE(offsetof({classname}_Config, {fname}), "{name}", 0, INT64_MAX),',
        "Int": 'P_IRANGE(offsetof({classname}_Config, {fname}), "{name}", INT64_MIN, INT64_MAX),',
        "Float": 'P_FRANGE(offsetof({classname}_Config, {fname}), "{name}", 0.0, 0.0),',
        "Bool": 'P_BOOL(offsetof({classname}_Config, {fname}), "{name}"),',
        "Color": 'P_COLOR(offsetof({classname}_Config, {fname}), "{name}"),',
        "ColorList": 'P_LIST<{classname}_Color_Config>(offsetof({classname}_Config, {fname}), "{name}", color_params, num_color_params, 1, 16),',
        "SizeString": 'P_STRING(offsetof({classname}_Config, {fname}), "{name}"),',
        "NtString": 'P_STRING(offsetof({classname}_Config, {fname}), "{name}"),',
        "Map4": 'P_SELECT(offsetof({classname}_Config, {fname}), "{name}", {fname}s),',
        "Map8": 'P_SELECT(offsetof({classname}_Config, {fname}), "{name}", {fname}s),',
        "_generic": 'PARAM(offsetof({classname}_Config, {fname}), AVS_PARAM_INVALID, "{name}"),',
    }
    p_macros_code = [
        'P_STRING(offsetof({classname}_Config, init), "Init", nullptr, recompile),',
        'P_STRING(offsetof({classname}_Config, frame), "Frame", nullptr, recompile),',
        'P_STRING(offsetof({classname}_Config, beat), "Beat", nullptr, recompile),',
        'P_STRING(offsetof({classname}_Config, point), "Point", nullptr, recompile),',
    ]
    g_macros = {
        "param": "const Parameter& p_{fname} = {classname}_Info::parameters[{index}];",
        "handle": "AVS_Parameter_Handle p_{fname} = {classname}_Info::parameters[{index}].handle;",
        "init_bool": "CheckDlgButton(hwndDlg, {ui_control}, g_this->get_bool(p_{fname}));",
        "init_int": """auto {fname} = g_this->get_int(p_{fname}.handle);
            init_ranged_slider(p_{fname}, {fname}, hwndDlg, {ui_control});""",
        "init_float": "// INIT_FLOAT: {fname}",
        "init_select": """auto {fname} = g_this->get_int(p_{fname}.handle);
            static constexpr size_t num_{fname}s = NNN;
            uint32_t controls_{fname}[num_{fname}s] = {{FILLME}};
            init_select_radio(p_{fname}, {fname}, hwndDlg, controls_{fname}, num_{fname}s);""",
        "init_string": "SetDlgItemText(hwndDlg, {ui_control}, g_this->get_string(p_{fname}));",
        "init_color": "// INIT_COLOR: {fname}",
        "string_set_preamble": """if (!isstart && HIWORD(wParam) == EN_CHANGE) {{
                int length = 0;
                char* buf = NULL;
            """,
        "string_set_epilogue": """}}""",
        "set_bool": "case {ui_control}: g_this->set_bool(p_{fname}, IsDlgButtonChecked(hwndDlg, {ui_control})); break;",
        "set_select": """g_this->set_int(p_{fname}.handle, SendMessage((HWND)lParam, CB_GETCURSEL, 0, 0));""",
        "set_string": """case {ui_control}:
                        length = GetWindowTextLength((HWND)lParam) + 1;
                        buf = new char[length];
                        GetDlgItemText(hwndDlg, {ui_control}, buf, length);
                        g_this->set_string(p_{fname}.handle, buf);
                        delete[] buf;
                        break;""",
        "set_int": """{else_}if (control == GetDlgItem(hwndDlg, {ui_control})) {{
                g_this->set_int(p_{fname}.handle, value);
            }}""",
        "set_float": "// SET_FLOAT: {fname}",
        "set_color": "// SET_COLOR: {fname}",
    }
    options_macro = """static const char* const* {fname}s(int64_t* length_out) {{
        *length_out = {options_count};
        static const char* const options[{options_count}] = {{
            {options}
        }};
        return options;
    }};
"""

    def __init__(
        self,
        name: str,
        type_: str
        | int
        | tuple[str, int]
        | tuple[str, dict[str, str]]
        | tuple[str, int | list[int], str],
    ):
        self.name = name
        self.type_: str
        self.type_config: Optional[str | dict[str, str] | int | list[int]] = None
        self.type_filter: Optional[str] = None
        if isinstance(type_, tuple):
            self.type_config = type_[1]
            if len(type_) > 2:
                self.type_filter = cast(str, type_[2])
            self.type_ = type_[0]
        elif isinstance(type_, int):
            self.type_config = type_ * 8
            self.type_ = "Uint"
        elif type_ == "Int32":
            self.type_ = "Int"
            self.type_config = 32
        else:
            self.type_ = type_
        self.is_select = False
        self.options: dict[str, str]
        if self.type_ in tables:
            self.is_select = True
            self.options = tables[self.type_]
            if isinstance(list(self.options.values())[0], list):
                self.options = {k: v[0] for k, v in self.options.items()}
        if self.type_filter and self.type_filter in tables:
            self.is_select = True
            self.options = tables[self.type_filter]
            self.type_filter = None
        if self.type_filter == "Boolified":
            self.type_ = "Bool"
        if self.type_filter == "SemiColSplit":
            pass
        if self.type_ in ["Map4", "Map8"] and isinstance(self.type_config, dict):
            self.is_select = True
            self.options = self.type_config
            self.type_config = None

    def as_config(self, classname: str, subconfig: str) -> list[str]:
        macro: Sequence[str]
        if isinstance(self.type_, str) and "Code" in self.type_:
            macro = self.c_macros_code
        elif self.is_select:
            macro = [self.c_macros["Select"]]
        elif isinstance(self.type_, str):
            macro = [self.c_macros.get(self.type_, self.c_macros["_invalid"])]
        return [
            m.format(
                fname=camel_to_snake(self.name),
                classname=classname,
                subconfig=subconfig,
            )
            for m in macro
        ]

    def options_func(self) -> str:
        if not self.is_select:
            return ""
        return self.options_macro.format(
            fname=camel_to_snake(self.name),
            options_count=len(self.options),
            options=("\n" + " " * 4 * 3).join(
                '"' + str(o).replace("_", " ").title() + '",'
                for _, o in self.options.items()
            ),
        )

    def as_parameter(self, classname: str) -> list[str]:
        if "Code" in self.type_:
            macro = self.p_macros_code
        elif self.is_select:
            macro = [self.p_macros["Map4"]]
        else:
            macro = [self.p_macros.get(self.type_, self.p_macros["_generic"])]
        return [
            m.format(
                classname=classname,
                fname=camel_to_snake(self.name),
                name=" ".join(split_camel(self.name)).title(),
            )
            for m in macro
        ]

    def g_param_decl(self, classname: str, index: int) -> str:
        if self.type_ in ["List", "Map4", "Map8", "Uint", "Int", "Float"]:
            return self.g_macros["param"].format(
                fname=camel_to_snake(self.name), classname=classname, index=index
            )
        else:
            return self.g_macros["handle"].format(
                fname=camel_to_snake(self.name), classname=classname, index=index
            )

    def g_param_init(self) -> str:
        if self.type_ in ["Bool"]:
            return self.g_macros["init_bool"].format(
                fname=camel_to_snake(self.name),
                ui_control=f"IDC_{camel_to_snake(self.name).upper()}",
            )
        elif self.type_ in ["Uint", "Int"]:
            return self.g_macros["init_int"].format(
                fname=camel_to_snake(self.name),
                ui_control=f"IDC_{camel_to_snake(self.name).upper()}",
            )
        elif self.type_ in ["Float"]:
            return self.g_macros["init_float"].format(
                fname=camel_to_snake(self.name),
                ui_control=f"IDC_{camel_to_snake(self.name).upper()}",
            )
        elif self.type_ in ["Color"]:
            return self.g_macros["init_color"].format(
                fname=camel_to_snake(self.name),
                ui_control=f"IDC_{camel_to_snake(self.name).upper()}",
            )
        elif self.type_ in ["SizeString", "NtString"]:
            return self.g_macros["init_string"].format(
                fname=camel_to_snake(self.name),
                ui_control=f"IDC_{camel_to_snake(self.name).upper()}",
            )
        elif self.type_ in ["Select", "Map4", "Map8"]:
            return self.g_macros["init_select"].format(
                fname=camel_to_snake(self.name),
                ui_control=f"IDC_{camel_to_snake(self.name).upper()}",
            )
        else:
            print("param init not implemented:", self.type_)
            return ""
        # "ColorList"
        # "Int_array"
        # "Float_array"
        # "Color_array"

    def g_param_set(self, is_first: bool = False) -> str:
        if self.type_ in ["Bool"]:
            return self.g_macros["set_bool"].format(
                fname=camel_to_snake(self.name),
                ui_control=f"IDC_{camel_to_snake(self.name).upper()}",
            )
        elif self.type_ in ["Uint", "Int"]:
            return self.g_macros["set_int"].format(
                fname=camel_to_snake(self.name),
                ui_control=f"IDC_{camel_to_snake(self.name).upper()}",
                else_="" if is_first else "else ",
            )
        elif self.type_ in ["Float"]:
            return self.g_macros["set_float"].format(
                fname=camel_to_snake(self.name),
                ui_control=f"IDC_{camel_to_snake(self.name).upper()}",
            )
        elif self.type_ in ["Color"]:
            return self.g_macros["set_color"].format(
                fname=camel_to_snake(self.name),
                ui_control=f"IDC_{camel_to_snake(self.name).upper()}",
            )
        elif self.type_ in ["SizeString", "NtString"]:
            return self.g_macros["set_string"].format(
                fname=camel_to_snake(self.name),
                ui_control=f"IDC_{camel_to_snake(self.name).upper()}",
            )
        elif self.type_ in ["Select", "Map4", "Map8"]:
            return self.g_macros["set_select"].format(
                fname=camel_to_snake(self.name),
                ui_control=f"IDC_{camel_to_snake(self.name).upper()}",
            )
        else:
            print("param set not implemented:", self.type_)
            return ""


class Component:
    colorlist_config = """struct {classname}_Color_Config : public Effect_Config {{
    uint64_t color = 0x000000;
    {classname}_Color_Config() = default;
    {classname}_Color_Config(uint64_t color) : color(color){{}};
}};
"""
    colorlist_initialize = (
        "{classname}_Config() {{ this->colors.emplace_back(0xffffff); }}"
    )
    colorlist_params = """static constexpr uint32_t num_color_params = 1;
    static constexpr Parameter color_params[num_color_params] = {{
        P_COLOR(offsetof({classname}_Color_Config, color), "Color"),
    }};
"""
    callback_decl_ = (
        "static void callback(Effect*, const Parameter*, const std::vector<int64_t>&);"
    )
    recompile_decl_ = (
        "static void recompile(Effect*, const Parameter*, const std::vector<int64_t>&);"
    )
    recompile_impl_ = """void {classname}_Info::recompile(Effect* component, const Parameter* parameter, std::vector<int64_t>&) {{
    auto {varname} = (E_{classname}*)component;
    if (std::string("Init") == parameter->name) {{
        {varname}->code_init.need_recompile = true;
    }} else if (std::string("Frame") == parameter->name) {{
        {varname}->code_frame.need_recompile = true;
    }} else if (std::string("Beat") == parameter->name) {{
        {varname}->code_beat.need_recompile = true;
    }} else if (std::string("Point") == parameter->name) {{
        {varname}->code_point.need_recompile = true;
    }}
    {varname}->recompile_if_needed();
}}
"""
    vars_struct_ = """struct {classname}_Vars : public Variables {{
    double* w;
    double* h;

    virtual void register_(void*);
    virtual void init(int, int, int, va_list);
}};
"""

    g_param_header = "    auto g_this = (E_{classname}*)g_current_render;"
    g_options_init = """    int64_t options_length;
    const char* const* options;"""
    g_params_handle = """{options_init}
    switch(uMsg) {{
        case WM_INITDIALOG: {{
            {params_init}
            return 1;
        }}
        case WM_COMMAND: {{
            switch (LOWORD(wParam)) {{
                {params_set}
            }}
            return 0;
        }}
        case WM_HSCROLL: {{
            HWND control = (HWND)lParam;
            int value = (int)SendMessage(control, TBM_GETPOS, 0, 0);
            {params_slider_set}
            return 0;
        }}
    }}
"""

    def __init__(self, obj: dict):
        self.name = obj.get("name")
        _id = obj.get("code")
        self.effect_id = -1
        self.ape_id = "nullptr"
        if isinstance(_id, list):
            self.ape_id = '"' + "".join([chr(c) for c in _id if c > 0]) + '"'
        elif isinstance(_id, int):
            self.effect_id = _id
        self.group = obj.get("group", "")
        self.func = obj.get("func")
        self.fields = [
            Field(k, tuple(v) if isinstance(v, list) else v)
            for k, v in obj.get("fields", {}).items()
            if k not in ["enabled", "new_version"] and not k.startswith("null")
        ]
        self.is_codeable = any("Code" in f.type_ for f in self.fields)

    def configs(self, classname, subtype):
        params = []
        for f in self.fields:
            params += f.as_config(classname, subtype)
        return params

    def options(self):
        return [f.options_func() for f in self.fields if f.is_select]

    def parameters(self, classname):
        params = []
        for f in self.fields:
            params += f.as_parameter(classname)
        return params

    def callback_decl(self):
        return self.callback_decl_

    def recompile_decl(self):
        return self.recompile_decl_ if self.is_codeable else ""

    def recompile_impl(self, classname):
        if self.is_codeable:
            return self.recompile_impl_.format(
                varname=classname.lower(), classname=classname
            )
        else:
            return ""

    def vars_struct(self, classname):
        return self.vars_struct_.format(classname=classname) if self.is_codeable else ""

    def gui_parameters(self, classname: str) -> str:
        params = self.g_param_header.format(classname=classname)
        params += "\n"
        for i, f in enumerate(self.fields):
            params += "    " + f.g_param_decl(classname, i)
            params += "\n"
        return params

    def gui_init(self, classname: str) -> str:
        params_init = ""
        params_set = ""
        params_slider_set = ""
        options_init = ""
        if any(f.type_ == "Select" for f in self.fields):
            options_init = self.g_options_init

        is_first_slider = True
        for f in self.fields:
            params_init += f.g_param_init() + "\n" + " " * 4 * 3
            if f.type_ in ["Uint", "Int"]:
                params_slider_set += f.g_param_set(is_first_slider) + " "
                is_first_slider = False
            else:
                params_set += f.g_param_set() + "\n" + " " * 4 * 4

        return self.g_params_handle.format(
            options_init=options_init,
            params_init=params_init,
            params_set=params_set,
            params_slider_set=params_slider_set,
        )


def components():
    data = {}
    with open("components.json") as f:
        data = json.load(f)
    return [Component(c) for c in data]


def main(name):
    split_name = split_camel(name)
    for c in components():
        c_name = c.name.split()
        if all(n in cn for n, cn in zip_longest(split_name, c_name, fillvalue="")):
            classname = "".join(split_name)
            colorlist_config = ""
            colorlist_initialize = ""
            colorlist_params = ""
            if any(f.type_ == "ColorList" for f in c.fields):
                colorlist_config = Component.colorlist_config
                colorlist_initialize = Component.colorlist_initialize
                colorlist_params = Component.colorlist_params
            args = {
                "base": "Programmable" if c.is_codeable else "Configurable",
                "classname": classname,
                "group": c.group,
                "displayname": " ".join(c_name),
                "effect_id": c.effect_id,
                "ape_id": c.ape_id,
                "varname": classname.lower(),
                "config_fields": ("\n" + " " * 4).join(c.configs(classname, "SUBTYPE")),
                "select_option_funcs": ("\n" + " " * 4).join(c.options()),
                "parameter_count": len(c.fields) + c.is_codeable * 3,
                "parameters": ("\n" + " " * 8).join(c.parameters(classname)),
                "enums": "",
                "colorlist_config": colorlist_config.format(classname=classname),
                "colorlist_initialize": colorlist_initialize.format(
                    classname=classname
                ),
                "colorlist_params": colorlist_params.format(classname=classname),
                "callback_decl": c.callback_decl(),
                "recompile_decl": c.recompile_decl(),
                "recompile_impl": c.recompile_impl(classname),
                "vars_struct": c.vars_struct(classname),
                "vars_inheritance": f", {classname}_Vars" if c.is_codeable else "",
                "gui_parameters": c.gui_parameters(classname),
                "gui_init": c.gui_init(classname),
            }
            print(template().format(**args))
            return


def template():
    return """#pragma once

#include "effect.h"
#include "effect_info.h"

{enums}
{colorlist_config}
struct {classname}_Config : public Effect_Config {{
    {config_fields}
    {colorlist_initialize}
}};

struct {classname}_Info : public Effect_Info {{
    static constexpr char const* group = "{group}";
    static constexpr char const* name = "{displayname}";
    static constexpr char const* help = "";
    static constexpr int32_t legacy_id = {effect_id};
    static constexpr char const* legacy_ape_id = {ape_id};

    {select_option_funcs}
    {colorlist_params}
    {callback_decl}
    {recompile_decl}
    static constexpr uint32_t num_parameters = {parameter_count};
    static constexpr Parameter parameters[num_parameters] = {{
        {parameters}
    }};

    EFFECT_INFO_GETTERS;
}};

{vars_struct}
class E_{classname} : public {base}_Effect<{classname}_Info, {classname}_Config{vars_inheritance}> {{
   public:
    E_{classname}();
    virtual ~E_{classname}();
    virtual int render(char visdata[2][2][576],
                       int is_beat,
                       int* framebuffer,
                       int* fbout,
                       int w,
                       int h);
    virtual void load_legacy(unsigned char* data, int len);
    virtual int save_legacy(unsigned char* data);

    // ...
}};

// --------------------------


constexpr Parameter {classname}_Info::parameters[];

void {classname}_Info::callback(Effect* component, const Parameter*, const std::vector<int64_t>&) {{
    auto {varname} = (E_{classname}*)component;
    {varname}->callback();
}}
{recompile_impl}

Effect_Info* create_{classname}_Info() {{ return new {classname}_Info(); }}
Effect* create_{classname}() {{ return new E_{classname}(); }}
void set_{classname}_desc(char* desc) {{ E_{classname}::set_desc(desc); }}

// --------------------------

{gui_parameters}

{gui_init}
"""


if __name__ == "__main__":
    name = "DMove"
    if len(sys.argv) > 1:
        name = sys.argv[1]
    main(name)
