# setup.py
from setuptools import setup, find_packages

setup(
    name="kidscompass",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "ntplib",
        "python-dateutil",
        "PySide6",
        "matplotlib",
        "reportlab",
    ],
    entry_points={
        "console_scripts": [
            "kidscompass=kidscompass.main:run_wizard",
        ],
    },
)
