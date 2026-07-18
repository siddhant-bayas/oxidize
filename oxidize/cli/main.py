import click

from oxidize.cli.commands.add import cmd_add
from oxidize.cli.commands.bisect import cmd_bisect
from oxidize.cli.commands.blame import cmd_blame
from oxidize.cli.commands.branch import cmd_branch
from oxidize.cli.commands.checkout import cmd_checkout
from oxidize.cli.commands.commit import cmd_commit
from oxidize.cli.commands.diff import cmd_diff
from oxidize.cli.commands.hooks import cmd_hooks
from oxidize.cli.commands.ignores import cmd_ignores
from oxidize.cli.commands.init import cmd_init
from oxidize.cli.commands.log import cmd_log
from oxidize.cli.commands.merge import cmd_merge
from oxidize.cli.commands.notebook import cmd_notebook_diff
from oxidize.cli.commands.remote import cmd_remote
from oxidize.cli.commands.resolve import cmd_resolve
from oxidize.cli.commands.scan import cmd_scan
from oxidize.cli.commands.show import cmd_show
from oxidize.cli.commands.stash import cmd_stash
from oxidize.cli.commands.status import cmd_status
from oxidize.cli.commands.tag import cmd_tag
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
cli.add_command(cmd_show, "show")
cli.add_command(cmd_scan, "scan")
cli.add_command(cmd_undo, "undo")
cli.add_command(cmd_ignores, "ignores")
cli.add_command(cmd_branch, "branch")
cli.add_command(cmd_checkout, "checkout")
cli.add_command(cmd_tag, "tag")
cli.add_command(cmd_merge, "merge")
cli.add_command(cmd_resolve, "resolve")
cli.add_command(cmd_stash, "stash")
cli.add_command(cmd_bisect, "bisect")
cli.add_command(cmd_hooks, "hooks")
cli.add_command(cmd_blame, "blame")
cli.add_command(cmd_notebook_diff, "notebook-diff")
cli.add_command(cmd_remote, "remote")
