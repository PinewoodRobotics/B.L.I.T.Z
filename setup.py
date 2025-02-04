from setuptools import setup, find_packages

setup(
    name="BLITZ",
    version="0.1",
    packages=find_packages(include=["generated*", "project*"]),
)
