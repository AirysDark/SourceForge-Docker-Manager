# docker_support/dockerfile_parser.py

import os


class DockerfileParser:
    def __init__(self, dockerfile_path="Dockerfile"):
        self.path = dockerfile_path

    def parse(self):
        if not os.path.exists(self.path):
            raise FileNotFoundError(self.path)

        instructions = []

        with open(self.path, "r") as f:
            for line in f:
                line = line.strip()

                # Skip comments / empty
                if not line or line.startswith("#"):
                    continue

                parts = line.split(maxsplit=1)
                cmd = parts[0].upper()
                arg = parts[1] if len(parts) > 1 else ""

                if cmd == "FROM":
                    instructions.append({
                        "type": "FROM",
                        "image": arg
                    })

                elif cmd == "COPY":
                    src, dest = arg.split()
                    instructions.append({
                        "type": "COPY",
                        "src": src,
                        "dest": dest
                    })

                elif cmd == "RUN":
                    instructions.append({
                        "type": "RUN",
                        "cmd": arg
                    })

                else:
                    raise ValueError(f"Unsupported Dockerfile command: {cmd}")

        return instructions