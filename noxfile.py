import nox
from pathlib import Path

nox.options.default_venv_backend = "uv"
nox.options.reuse_existing_virtualenvs = True

SCRIPTS_DIR = Path("scripts")
# Each subfolder of scripts/ with a download.py is a dataset
ALL_DATASETS = sorted(p.name for p in SCRIPTS_DIR.iterdir() if p.is_dir() and (p / "download.py").exists())


@nox.session
def download(session):
    """Download data. Use `-- <name>` to run a single dataset."""
    session.install("-r", "requirements.txt")
    datasets = session.posargs or ALL_DATASETS
    for name in datasets:
        if name not in ALL_DATASETS:
            session.error(f"Unknown dataset: {name}. Available: {ALL_DATASETS}")
        session.run("python", f"scripts/{name}/download.py")
        validate = SCRIPTS_DIR / name / "validate.py"
        session.run("python", str(validate))
