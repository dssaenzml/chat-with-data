import uvicorn
from uvicorn.config import Config
from uvicorn.supervisors.watchfilesreload import WatchFilesReload

class CustomWatchFilesReload(WatchFilesReload):
    def __init__(self, config: Config, target: str, sockets: list, **kwargs):
        # Exclude .venv directory from watching
        if hasattr(config, 'reload_excludes'):
            config.reload_excludes.append('.venv')
        else:
            config.reload_excludes = ['.venv']
        super().__init__(config, target, sockets, **kwargs)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_excludes=[".venv", ".venv/*", "__pycache__", "*.pyc"],
        reload_delay=1.0
    ) 