from ngapp import AppConfig
from . import __version__, BeamSolver

_DESCRIPTION = "App descrition shown in preview"

config = AppConfig(
    name="Beam Solver",
    version=__version__,
    python_class=BeamSolver,
    frontend_pip_dependencies=["ngsolve", "ngsolve_webgpu"],
    description=_DESCRIPTION,
)
