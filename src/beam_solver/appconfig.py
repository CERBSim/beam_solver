from ngapp import AppAccessConfig, AppConfig
from . import __version__, BeamSolver

_DESCRIPTION = "App descrition shown in preview"

config = AppConfig(
    name="Beam Solver",
    version=__version__,
    python_class=BeamSolver,
    frontend_pip_dependencies=[],
    frontend_dependencies=[],
    description=_DESCRIPTION,
    compute_environments=[],
    access=AppAccessConfig(),
)
