"""Inspect the final runtime image, never print file contents or layer commands."""
from __future__ import annotations

import re
import subprocess
import sys

from scripts.check_public_artifact import FORBIDDEN

EXPECTED = re.compile(
    r"/srv/demo/(?:app/dist/(?:index\.html|gemesislogo\.jpg|assets/[\w-]+\.(?:js|css))"
    r"|demo/[a-z_]+\.py|(?:common|fts_index|rate_limit|tools_search|mcp_server)\.py"
    r"|requirements-demo\.txt)$"
)


def inspect(image: str) -> None:
    user = subprocess.check_output(
        ["docker", "image", "inspect", "--format", "{{.Config.User}}", image], text=True,
    ).strip()
    if user != "10001":
        raise RuntimeError("runtime-user")
    paths = subprocess.check_output(
        ["docker", "run", "--rm", "--entrypoint", "find", image, "/srv/demo", "-type", "f"], text=True,
    ).splitlines()
    if not paths or any(not EXPECTED.fullmatch(path) for path in paths):
        raise RuntimeError("unreviewed-runtime-files")
    layers = subprocess.check_output(
        ["docker", "image", "history", "--no-trunc", "--format", "{{.CreatedBy}}", image], text=True,
    )
    for rule, signature in FORBIDDEN.items():
        if signature in layers:
            raise RuntimeError(f"image-layer-{rule}")
    print(f"Container artifact: {len(paths)} reviewed files, unprivileged user, clean layer history.")


if __name__ == "__main__":
    try:
        inspect(sys.argv[1] if len(sys.argv) == 2 else "gemesis-demo:local")
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Image inspection failed ({type(exc).__name__}{': ' + str(exc) if isinstance(exc, RuntimeError) else ''})")
        raise SystemExit(1)
