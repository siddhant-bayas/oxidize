from __future__ import annotations

from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import NestedCompleter, PathCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style

from oxidize.core.repository import Repository, RepositoryNotFound

_STYLE = Style.from_dict(
    {
        "toolbar": "#ffffff bg:#333333 bold",
        "prompt": "#00aa00 bold",
    }
)

_HISTORY_PATH = Path.home() / ".oxidize_history"


def _get_toolbar() -> HTML:
    try:
        repo = Repository.discover()
        branch = repo.refs.current_branch() or "detached"
        staged = len(repo.index)
        head = repo.refs.head()
        short = head[:8] if head else "none"
        return HTML(
            f" <b>({branch})</b> "
            f"staged:<b>{staged}</b> "
            f"HEAD:<b>{short}</b> "
            f"| <b>Ctrl-D</b> exit | <b>help</b> for commands"
        )
    except RepositoryNotFound:
        return HTML(" <b>no repo</b> | <b>oxidize init</b> to create one | <b>Ctrl-D</b> exit")


def _build_completer() -> NestedCompleter:
    command_names = [
        "init",
        "add",
        "status",
        "commit",
        "log",
        "diff",
        "scan",
        "help",
        "exit",
        "quit",
        "undo",
        "redo",
        "branch",
        "agent",
        "blame",
        "merge",
        "show",
    ]
    alias_map: dict[str, None] = {
        "s": None,
        "c": None,
        "a": None,
        "l": None,
        "d": None,
        "q": None,
    }
    nested: dict[str, PathCompleter | None] = {cmd: PathCompleter() for cmd in command_names}
    nested.update(alias_map)
    return NestedCompleter.from_nested_dict(nested)


_ALIASES: dict[str, str] = {
    "s": "status",
    "c": "commit",
    "a": "add",
    "l": "log",
    "d": "diff",
    "q": "exit",
}


def _dispatch(line: str) -> str | None:
    parts = line.strip().split()
    if not parts:
        return None

    cmd = _ALIASES.get(parts[0], parts[0])
    args = parts[1:]

    if cmd in ("exit", "quit"):
        return "__EXIT__"

    if cmd == "help":
        return _help_text()

    try:
        from click.testing import CliRunner
        from oxidize.cli.main import cli

        runner = CliRunner()
        result = runner.invoke(cli, [cmd] + args, catch_exceptions=False)
        return result.output
    except SystemExit as e:
        return f"(exit code {e.code})" if e.code else None
    except Exception as e:
        return f"error: {e}"


def _help_text() -> str:
    return """\
Available commands:
  init [path]       Initialize a new repository
  add <paths...>    Stage files for commit
  status (s)        Show working tree status
  commit -m "msg"   Record staged changes (c)
  log [-n N]        Show commit history (l)
  diff [paths]      Show changes (d)
  scan [paths]      Scan for secrets
  help              Show this help
  exit (q)          Exit the shell

Aliases: s=status, c=commit, a=add, l=log, d=diff, q=exit
"""


def main() -> None:
    import sys

    args = sys.argv[1:]
    if args:
        from oxidize.cli.main import cli

        cli(args, standalone_mode=True)
        return

    session: PromptSession[str] = PromptSession(
        history=FileHistory(str(_HISTORY_PATH)),
        completer=_build_completer(),
        complete_while_typing=True,
        style=_STYLE,
        bottom_toolbar=_get_toolbar,
    )

    print("oxidize interactive shell v0.1.0")
    print("Type 'help' for commands, Ctrl-D to exit.\n")

    while True:
        try:
            text = session.prompt("oxi> ")
        except KeyboardInterrupt:
            continue
        except EOFError:
            break

        text = text.strip()
        if not text:
            continue

        output = _dispatch(text)
        if output == "__EXIT__":
            break
        if output:
            print(output, end="" if output.endswith("\n") else "\n")


if __name__ == "__main__":
    main()
