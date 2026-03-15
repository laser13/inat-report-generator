"""Publish report assets to GitHub Pages and produce final article with absolute URLs."""

import re
import subprocess
from pathlib import Path

import typer


def publish_to_gh_pages(
    report_dir: Path,
    slug: str,
    year: str,
    repo_url: str | None = None,
) -> str:
    """Push charts and maps to gh-pages branch and return base URL.

    Args:
        report_dir: Path to reports/{slug}/{year}/
        slug: Dataset slug
        year: Year string (or "all-time")
        repo_url: Git remote URL (auto-detected if None)

    Returns:
        Base URL for assets on GitHub Pages.
    """
    # Detect repo info from git remote
    if repo_url is None:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
        repo_url = result.stdout.strip()

    # Parse GitHub user/repo from URL
    match = re.search(r"github\.com[:/](.+?)/(.+?)(?:\.git)?$", repo_url)
    if not match:
        raise ValueError(f"Cannot parse GitHub URL: {repo_url}")
    gh_user, gh_repo = match.group(1), match.group(2)

    base_url = f"https://{gh_user}.github.io/{gh_repo}"
    assets_path = f"reports/{slug}/{year}"

    # Collect files to publish (charts + maps)
    charts_dir = report_dir / "charts"
    maps_dir = report_dir / "maps"
    files_to_push: list[Path] = []
    if charts_dir.exists():
        files_to_push.extend(charts_dir.glob("*.png"))
    if maps_dir.exists():
        files_to_push.extend(maps_dir.glob("*.html"))

    if not files_to_push:
        typer.echo("No assets to publish.", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Publishing {len(files_to_push)} files to gh-pages...")

    # Use git worktree for gh-pages branch
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Check if gh-pages branch exists
        branch_check = subprocess.run(
            ["git", "rev-parse", "--verify", "gh-pages"],
            capture_output=True,
            text=True,
        )

        if branch_check.returncode != 0:
            # Create orphan gh-pages branch
            typer.echo("  Creating gh-pages branch...")
            subprocess.run(
                ["git", "checkout", "--orphan", "gh-pages"],
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "rm", "-rf", "."],
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "--allow-empty", "-m", "init gh-pages"],
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "checkout", "-"],
                capture_output=True,
                check=True,
            )

        # Add worktree
        worktree_path = tmp / "gh-pages"
        subprocess.run(
            ["git", "worktree", "add", str(worktree_path), "gh-pages"],
            capture_output=True,
            check=True,
        )

        try:
            # Copy files
            dest_dir = worktree_path / assets_path
            for src in files_to_push:
                rel = src.relative_to(report_dir)
                dst = dest_dir / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(src.read_bytes())
                typer.echo(f"  {rel}")

            # Commit and push
            subprocess.run(
                ["git", "-C", str(worktree_path), "add", "-A"],
                capture_output=True,
                check=True,
            )

            # Check if there are changes
            diff = subprocess.run(
                ["git", "-C", str(worktree_path), "diff", "--cached", "--quiet"],
                capture_output=True,
            )
            if diff.returncode == 0:
                typer.echo("  No changes to push.")
            else:
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(worktree_path),
                        "commit",
                        "-m",
                        f"Update assets: {slug}/{year}",
                    ],
                    capture_output=True,
                    check=True,
                )
                typer.echo("  Pushing to gh-pages...")
                subprocess.run(
                    ["git", "-C", str(worktree_path), "push", "origin", "gh-pages"],
                    capture_output=True,
                    check=True,
                )
        finally:
            # Cleanup worktree
            subprocess.run(
                ["git", "worktree", "remove", str(worktree_path)],
                capture_output=True,
            )

    return f"{base_url}/{assets_path}"


def make_publishable_html(
    article_path: Path,
    output_path: Path,
    base_url: str,
) -> Path:
    """Replace relative asset paths in article.html with absolute GitHub Pages URLs.

    Args:
        article_path: Path to article.html with relative paths
        output_path: Where to write the publishable version
        base_url: GitHub Pages base URL for assets
    """
    html = article_path.read_text(encoding="utf-8")

    # Replace relative chart/map paths with absolute URLs
    html = html.replace('src="charts/', f'src="{base_url}/charts/')
    html = html.replace('href="charts/', f'href="{base_url}/charts/')
    html = html.replace('href="maps/', f'href="{base_url}/maps/')

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path
