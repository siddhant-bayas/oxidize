import click

from oxidize.cli.commands.add import cmd_add
from oxidize.cli.commands.commit import cmd_commit
from oxidize.cli.commands.diff import cmd_diff
from oxidize.cli.commands.init import cmd_init
from oxidize.cli.commands.log import cmd_log
from oxidize.cli.commands.scan import cmd_scan
from oxidize.cli.commands.status import cmd_status
from oxidize.cli.commands.undo import cmd_undo


@click.group()
@click.version_option(package_name="oxidize")
def cli() -> None:
    """oxidize -- a version control system with semantic awareness."""


cli.add_command(cmd_init, "init")
cli.add_command(cmd_add, "add")
cli.add_command(cmd_status, "status")
cli.add_command(cmd_commit, "commit")
cli.add_command(cmd_log, "log")
cli.add_command(cmd_diff, "diff")
cli.add_command(cmd_scan, "scan")
cli.add_command(cmd_undo, "undo")
