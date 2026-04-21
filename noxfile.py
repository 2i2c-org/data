from pathlib import Path

import nox

nox.options.default_venv_backend = "uv"
nox.options.reuse_existing_virtualenvs = True

SCRIPTS_DIR = Path("scripts")
DOCS_DIR = Path("docs")
# Each subfolder of scripts/ with a download.py is a dataset
# (yes right now this is only one folder but the pattern is here in case we want to extend it!)
ALL_DATASETS = sorted(
    p.name for p in SCRIPTS_DIR.iterdir() if p.is_dir() and (p / "download.py").exists()
)


def _resolve_datasets(session):
    """Resolve `-- <name>` positional args to a list of datasets, or all."""
    datasets = session.posargs or ALL_DATASETS
    for name in datasets:
        if name not in ALL_DATASETS:
            session.error(f"Unknown dataset: {name}. Available: {ALL_DATASETS}")
    return datasets


@nox.session
def download(session):
    """Download data, then validate. Use `-- <name>` to run a single dataset."""
    session.install("-r", "requirements.txt")
    for name in _resolve_datasets(session):
        session.run("python", f"scripts/{name}/download.py")
    test(session)


@nox.session
def test(session):
    """Validate already-downloaded data. Use `-- <name>` to run a single dataset."""
    session.install("-r", "requirements.txt")
    for name in _resolve_datasets(session):
        session.run("python", str(SCRIPTS_DIR / name / "validate.py"))


def _docs_prepare(session):
    """Shared setup for the two docs builds."""
    session.install("-r", "requirements.txt")
    session.chdir(str(DOCS_DIR))
    session.run("python", "_scripts/cloud/fetch_release.py")
    session.run("python", "_scripts/cloud/generate_pages.py")


@nox.session
def docs(session):
    """Build the public docs site into docs/_build/html/.
    """
    _docs_prepare(session)
    session.run("npx", "--yes", "--package=mystmd", "myst", "build", "--html", "--execute", external=True)

@nox.session(name="docs-live")
def docs_live(session):
    """Live-preview the docs. Takes a long time because it executes all the pages in serial!
    """
    _docs_prepare(session)
    session.run("npx", "--yes", "--package=mystmd", "myst", "start", "--execute", external=True)
