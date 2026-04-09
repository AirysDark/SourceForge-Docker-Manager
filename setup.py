from setuptools import setup, find_packages

setup(
    name="sourceforge_docker_manager",
    version="0.1.0",
    description="User-space Python container engine, Termux-compatible",
    author="AirysDark",
    packages=find_packages(),
    install_requires=[
        "dataclasses",
        "flask",
        "requests",
        "pyyaml",
        "uvicorn"
    ],
    entry_points={
        "console_scripts": [
            "sf-docker=sourceforge_docker_manager.main:main_cli"
        ]
    },
    python_requires=">=3.10",
)
