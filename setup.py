from setuptools import setup, find_packages

setup(
    name="sourceforge_docker_manager",
    version="0.1.0",
    description="User-space Python container engine, uDocker-style",
    author="AirysDark",
    packages=find_packages(),
    install_requires=[
        "Starlette",
        "uvicorn",
        "pyyaml",   # keep only packages that need compilation/wheels
    ],
    entry_points={
        "console_scripts": [
            "sf-docker=sourceforge_docker_manager.main:main_cli"
        ]
    },
    python_requires=">=3.13",
)
