# -*- coding: utf-8 -*-
# -- This file is part of the Apio project
# -- (C) 2016-2024 FPGAwars
# -- Authors
# --  * Jesús Arroyo (2016-2019)
# --  * Juan Gonzalez (obijuan) (2019-2024)
# -- Licence GPLv2
"""Implementation of 'apio modify' command"""

from pathlib import Path
from varname import nameof
import click
from apio.managers.project import Project
from apio import cmd_util
from apio.commands import options
from apio.apio_context import ApioContext


# ---------------------------
# -- COMMAND
# ---------------------------
HELP = """
The command 'apio modify' has been deprecated. Please edit the 'apio.ini'
file manually with a text editor.
"""


# R0913: Too many arguments (6/5)
# pylint: disable=R0913
@click.command(
    "modify",
    short_help="[Depreciated] Modify the apio.ini project file.",
    help=HELP,
    cls=cmd_util.ApioCommand,
)
@click.pass_context
@options.board_option_gen(help="Set the board.")
@options.top_module_option_gen(help="Set the top level module name.")
@options.project_dir_option
def cli(
    cmd_ctx: click.core.Context,
    # Options
    board: str,
    top_module: str,
    project_dir: Path,
):
    """Modify the project file."""

    # At least one of these options are required.
    cmd_util.check_at_least_one_param(cmd_ctx, nameof(board, top_module))

    # -- Create the apio context.
    apio_ctx = ApioContext(project_dir=project_dir, load_project=False)

    # Create the apio.ini file
    ok = Project.modify_ini_file(
        apio_ctx.project_dir,
        board,
        top_module,
        apio_ctx.boards,
    )

    exit_code = 0 if ok else 1
    cmd_ctx.exit(exit_code)
