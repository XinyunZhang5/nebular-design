"""Local entry point. In production the process manager runs uvicorn directly.

The port comes from the environment because every host injects it that way — Fly,
Render and Railway all bind the container to a port they choose and pass it in as
$PORT. Hard-coding 8000 does not fail loudly: the container starts, the app
listens on a port nothing is routed to, and the platform reports a health check
timeout with no error in the application log.
"""

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        # Reload watches the filesystem and forks a second process. Useful locally,
        # a waste of memory on a box chosen for having barely enough.
        reload=os.environ.get("ENV", "development") == "development",
    )
