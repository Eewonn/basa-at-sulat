"""Start the engine: python -m app (run from engine/).

Listens on 127.0.0.1:$PORT, default 8000. The desktop app sets PORT to a free port.
"""

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=int(os.environ.get("PORT", "8000")))
