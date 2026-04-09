# docker_support/dockerfile_parser.py

import os
import json


class DockerInstruction:
    """
    Represents a single Dockerfile instruction.
    """

    def __init__(self, instr_type, **kwargs):
        self.type = instr_type.upper()
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_dict(self):
        """
        Convert instruction to dictionary.
        """
        result = {"type": self.type}
        for attr in self.__dict__:
            if attr != "type":
                result[attr] = getattr(self, attr)
        return result

    @classmethod
    def from_dict(cls, data):
        """
        Create instruction from dictionary.
        """
        instr_type = data.get("type", "")
        args = {k: v for k, v in data.items() if k != "type"}
        return cls(instr_type, **args)

    def to_json(self):
        """
        Convert instruction to JSON string.
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str):
        """
        Create instruction from JSON string.
        """
        data = json.loads(json_str)
        return cls.from_dict(data)


class DockerfileParser:
    """
    Parses a Dockerfile into a list of DockerInstruction objects.
    """

    def __init__(self, dockerfile_path="Dockerfile"):
        self.path = dockerfile_path

    def parse(self):
        """
        Read Dockerfile and return a list of DockerInstruction objects.
        """
        if not os.path.exists(self.path):
            raise FileNotFoundError(self.path)

        instructions = []

        with open(self.path, "r") as f:
            for line in f:
                line = line.strip()

                # Skip comments / empty lines
                if not line or line.startswith("#"):
                    continue

                parts = line.split(maxsplit=1)
                cmd = parts[0].upper()
                arg = parts[1] if len(parts) > 1 else ""

                if cmd == "FROM":
                    instructions.append(DockerInstruction("FROM", image=arg))

                elif cmd == "COPY":
                    src, dest = arg.split()
                    instructions.append(DockerInstruction("COPY", src=src, dest=dest))

                elif cmd == "RUN":
                    instructions.append(DockerInstruction("RUN", cmd=arg))

                else:
                    raise ValueError(f"Unsupported Dockerfile command: {cmd}")

        return instructions
