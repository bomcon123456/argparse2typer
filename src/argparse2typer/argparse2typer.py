from pathlib import Path
from typing import List, Set, Union

import argparse

from num2words import num2words

ignore_dst = ["help"]

kw_to_import_str = {
    "typer": "import typer",
    "path": "from pathlib import Path",
    "enum": "from enum import Enum",
}


def camelcase_to_snakecase(string: str):
    if "_" in string:
        temp = string.split("_")
        string = temp[0] + "".join(ele.title() for ele in temp[1:])
    return string


def _is_str_digit(string: str):
    if (isinstance(string, str) and string.isdigit()) or isinstance(string, int):
        return True
    return False


def _handle_actions(
    choices: List[Union[str, int]],
    parsed_str: List[str],
    imports: Set,
    enums: Set,
    var_name: str,
    default_val_str: str,
):
    imports.add("enum")
    enumclassname = var_name
    enumclassname = camelcase_to_snakecase(enumclassname)

    enumclassname += "Enum"
    enumclassname = enumclassname[0].upper() + enumclassname[1:]
    enum_class_str = [
        f"class {enumclassname}(str, Enum):",
    ]
    for choice in choices:
        if _is_str_digit(choice):
            choice_var = num2words(int(choice)).replace("-", "_")
            enum_class_str.append(f"\t{choice_var} = {int(choice)}")
        else:
            choice_var = str(choice)
            enum_class_str.append(f'\t{choice_var} = "{str(choice)}"')
    enums.append("\n".join(enum_class_str))

    if _is_str_digit(default_val_str):
        default_val_str = num2words(int(default_val_str)).replace("-", "_")
    return default_val_str, enumclassname


def _build_text_line(
    imports: Set,
    enums: Set,
    parsed_str: List[str],
    create_app: bool,
    get_args: bool,
    tabspace=2,
):
    result = []
    for key in imports:
        result.append(f"{kw_to_import_str[key]}\n")
    if len(imports) != 0:
        result.append("\n")
    if create_app:
        result.append("app = typer.Typer()\n\n")
    for line in enums:
        result.append(f"{line}\n\n")

    for line in parsed_str:
        result.append(f"{line}\n")
    result.append("):\n")
    if get_args:
        result.append("\targs=dict(locals())")
    else:
        result.append("\tpass")

    for i in range(len(result)):
        result[i] = result[i].replace("\t", " " * tabspace)
    return result


def _write_to_file(result: List[str], output_path: Path, override: bool = False):
    if output_path is not None:
        if output_path.exists() and not override:
            inp = input(f"{output_path} exists, do you want to override? (y/any)")
            if inp.lower() == "y":
                write = True
            else:
                write = False
        elif override:
            write = True
        if write:
            with open(output_path.as_posix(), "w") as f:
                f.writelines(result)


def _parse_type(
    arg_type: type, default_val_str: str, var_name: str, imports: List[str]
):
    if arg_type is None and default_val_str is not None:
        arg_type = type(default_val_str)
    if arg_type is None:
        arg_type = "<UNKNOWN>"
    else:
        arg_type = arg_type.__name__
    if ("dir" in var_name or "path" in var_name) and arg_type == "str":
        arg_type = "Path"
        imports.add("path")
    return arg_type


def _parse_option(option_strings: List[str], var_name: str):
    long_option, short_option = None, None
    for option_str in option_strings:
        if "--" in option_str:
            long_option = option_str
            if long_option.replace("--", "") == var_name:
                long_option = None
        else:
            short_option = option_str
    fulloption_str = f', "{long_option}"' if long_option else ""
    fulloption_str += f',"{short_option}"' if short_option else ""
    return fulloption_str


def argparse2typer(
    parser: argparse.ArgumentParser,
    output_path: Path = None,
    import_typer: bool = False,
    create_app: bool = False,
    get_args: bool = True,
    override_output: bool = False,
) -> List[str]:
    """ Porting argparse's ArgumentParser into TyperCLI

    Args:
        parser (argparse.ArgumentParser): The existing parser.
        output_path (Path, optional): Path to write ported code into new file. Defaults to None.
        import_typer (bool, optional): Import typer in the header. Defaults to False.
        create_app (bool, optional): Create typer app. Defaults to False.
        get_args (bool, optional): simulate args variable from argparse. Defaults to True.
        override_output (bool, optional): Override output_path if exist. Defaults to False.

    Returns:
        List[str]: The filescript using typer CLI
    """

    actions = parser._actions
    imports = set()
    if import_typer:
        imports.add("typer")

    parsed_str = [
        "@app.command()",
        "def main(",
    ]
    enums = []
    for action in actions:
        action: argparse._HelpAction
        if action.dest in ignore_dst:
            continue
        var_name = action.dest
        var_name = var_name.replace("-", "_")

        is_arg = action.required
        typer_type_str = "typer.Argument" if is_arg else "typer.Option"

        help_str = action.help
        if help_str is not None:
            help_str = help_str.replace('"', "'")
        help_str = f', help="{help_str}"' if help_str else ""

        default_val_str = action.default

        if action.choices:
            default_val_str, enumclassname = _handle_actions(
                choices=action.choices,
                parsed_str=parsed_str,
                imports=imports,
                enums=enums,
                var_name=var_name,
                default_val_str=default_val_str,
            )
            line = f"\t{var_name}: {enumclassname} = {typer_type_str}({enumclassname}.{default_val_str}{help_str}),"
            parsed_str.append(line)
        else:
            arg_type = _parse_type(
                arg_type=action.type,
                default_val_str=default_val_str,
                var_name=var_name,
                imports=imports,
            )
            fulloption_str = _parse_option(action.option_strings, var_name)

            if is_arg and default_val_str is None:
                default_val_str = "..."
            if isinstance(default_val_str, str):
                default_val_str = f'"{default_val_str}"'

            line = f"\t{var_name}: {str(arg_type)} = {typer_type_str}({default_val_str}{fulloption_str}{help_str}),"
            parsed_str.append(line)
    result = _build_text_line(
        imports=imports,
        enums=enums,
        parsed_str=parsed_str,
        create_app=create_app,
        get_args=get_args,
    )
    _write_to_file(result, output_path, override_output)
    return result
