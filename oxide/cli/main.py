import click

from oxide.cli.commands.add import cmd_add
from oxide.cli.commands.commit import cmd_commit
from oxide.cli.commands.init import cmd_init
from oxide.cli.commands.log import cmd_log
from oxide.cli.commands.status import cmd_status


@click.group()
@click.version_option(package_name="oxide-vcs")
def cli() -> None:
    """Oxide — a next-generation version control system."""


cli.add_command(cmd_init)
cli.add_command(cmd_add)
cli.add_command(cmd_status)
cli.add_command(cmd_commit)
cli.add_command(cmd_log)
