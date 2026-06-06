from setuptools import setup, find_packages

setup(
    name="chaosProbe",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "typer",
        "rich",
        "httpx",
        "pyyaml",
        "psutil",
        "sqlalchemy",
        "pydantic",
        "pydantic-settings",
        "prometheus-client",
        "redis",
        "psycopg2-binary",
    ],
    entry_points={
        "console_scripts": [
            "chaosctl=chaosProbe.cli.commands:app",
        ],
    },
)