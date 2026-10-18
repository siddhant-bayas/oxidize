from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import click

from oxidize.core.repository import Repository, RepositoryNotFound
from oxidize.exporter.git_export import GitExportError
from oxidize.importer.git_import import GitImportError, import_git


@click.command("clone")
@click.argument("source")
@click.argument("target", required=False, default=".")
def cmd_clone(source: str, target: str) -> None:
    """Clone a git repository into an oxidize repository."""
    target_path = Path(target).resolve()
    src_path = Path(source)

    # Local git repository: import directly.
    if src_path.exists() and (src_path / ".git").exists():
        if target_path.exists() and not any(target_path.iterdir()):
            pass
        try:
            if not (target_path / ".oxidize").exists():
                Repository.init(target_path)
            repo = Repository(target_path)
        except Exception:
            repo = Repository.init(target_path)
        try:
            import_git(src_path, repo)
        except GitImportError as e:
            raise click.ClickException(str(e))
        click.echo(f"cloned {source} -> {target}")
        return

    # Remote URL: git clone into temp, then import.
    tmp = Path(tempfile.mkdtemp())
    try:
        subprocess.run(["git", "clone", source, str(tmp / "repo")], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        raise click.ClickException(e.stderr.decode(errors="replace").strip() or "git clone failed")
    git_src = tmp / "repo"
    try:
        if not (target_path / ".oxidize").exists():
            Repository.init(target_path)
        repo = Repository(target_path)
    except Exception:
        repo = Repository.init(target_path)
    try:
        import_git(git_src, repo)
    except GitImportError as e:
        raise click.ClickException(str(e))
    click.echo(f"cloned {source} -> {target}")


@click.command("push")
@click.argument("target")
def cmd_push(target: str) -> None:
    """Export the current oxidize repository to a git repository/target."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

    tgt = Path(target)
    # Local git repository or new directory: export.
    if not ("://" in target or target.startswith("git@")):
        try:
            from oxidize.exporter.git_export import export_git

            count = export_git(repo, tgt.resolve())
        except GitExportError as e:
            raise click.ClickException(str(e))
        click.echo(f"exported {count} commits to {target}")
        return

    # Remote URL: export to temp then git push.
    tmp = Path(tempfile.mkdtemp())
    git_dir = tmp / "repo"
    try:
        from oxidize.exporter.git_export import export_git

        export_git(repo, git_dir)
    except GitExportError as e:
        raise click.ClickException(str(e))
    try:
        subprocess.run(
            ["git", "-C", str(git_dir), "remote", "add", "origin", target],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        subprocess.run(
            ["git", "-C", str(git_dir), "remote", "set-url", "origin", target],
            check=False,
            capture_output=True,
        )
    try:
        subprocess.run(
            ["git", "-C", str(git_dir), "push", "-u", "origin", "main"],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        raise click.ClickException(e.stderr.decode(errors="replace").strip() or "git push failed")
    click.echo(f"pushed to {target}")
