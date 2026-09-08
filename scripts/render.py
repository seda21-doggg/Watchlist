"""Render site/index.html from history + watchlist.json. Templating only."""
import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"
SITE = ROOT / "site"

_env = Environment(loader=FileSystemLoader(TEMPLATES))


def _fmt_market_cap(v):
    if v is None:
        return "—"
    for div, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if v >= div:
            return f"${v / div:.1f}{suffix}"
    return f"${v:,.0f}"


def _fmt_pct(v, digits=1):
    return "—" if v is None else f"{v:.{digits}f}%"


def _fmt_num(v, digits=1):
    return "—" if v is None else f"{v:.{digits}f}"


_env.filters["market_cap"] = _fmt_market_cap
_env.filters["pct"] = _fmt_pct
_env.filters["num"] = _fmt_num


def _gh_owner_repo():
    # GITHUB_REPOSITORY is set automatically inside GitHub Actions as "owner/repo".
    repo = os.environ.get("GITHUB_REPOSITORY", "your-username/Watchlist")
    owner, _, name = repo.partition("/")
    return owner, name or "Watchlist"


def render_site(date_iso, history_payload, watchlist):
    template = _env.get_template("watchlist_template.html")
    owner, repo = _gh_owner_repo()
    html = template.render(
        date=date_iso, items=history_payload["items"], watchlist=watchlist,
        gh_owner=owner, gh_repo=repo,
    )
    SITE.mkdir(exist_ok=True)
    (SITE / "index.html").write_text(html, encoding="utf-8")
    return html
