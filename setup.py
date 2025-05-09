from setuptools import setup, find_packages

setup(
    name="BLITZ",
    version="0.1",
    packages=find_packages(
        include=[
            "generated",
            "generated.*",
            "project",
            "project.*",
            "helper",
            "helper.*",
            "schema",
            "schema.*",
        ]
    ),
)
