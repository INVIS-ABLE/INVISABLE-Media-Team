"""HTTP API surface for INVISABLE OS."""

from invisable_os.api.desktop_routes import api_router
from invisable_os.api.remix_routes import remix_router
from invisable_os.api.routes import router

# The Remix department's routes live on the same router so the whole platform is
# exposed under one FastAPI app.
router.include_router(remix_router)

# The desktop apps (Command Centre + Studio Worker) talk to the stable /api/* surface.
router.include_router(api_router)

__all__ = ["router"]
