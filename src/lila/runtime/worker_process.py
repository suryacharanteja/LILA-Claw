"""Private worker boot with independently scheduled liveness and local work."""
import json
import msvcrt
import os
import sys


def main():
    descriptor = msvcrt.open_osfhandle(int(sys.argv[1]),os.O_RDONLY)
    with os.fdopen(descriptor,"rb") as pipe:
        data = pipe.read(8193)
    if len(data)>8192:
        raise ValueError("boot frame too large")
    boot = json.loads(data)
    import asyncio
    from lila.worker.process_loop import run
    try:
        asyncio.run(run(boot))
    except BaseException:
        # No credential-bearing request details or document content in child logs.
        os._exit(1)


if __name__ == "__main__":
    main()
