"""Start the real CPython process, avoiding Windows venv redirector PIDs."""
import sys
from pathlib import Path


def command(module, *arguments):
    packages = Path(__file__).resolve().parents[3]/".venv/Lib/site-packages"
    if not packages.is_dir():
        raise RuntimeError("development environment missing; bundled entry points are supplied in M7")
    # Paths and module names only, never credentials. Execute the qualified locked packages.
    bootstrap = (f"import site,sys,runpy; site.addsitedir({str(packages)!r}); "
        f"sys.path.insert(0,{str(packages)!r}); sys.argv=[{module!r}]+sys.argv[1:]; "
        f"runpy.run_module({module!r},run_name='__main__')")
    return [sys._base_executable,"-c",bootstrap,*arguments]
