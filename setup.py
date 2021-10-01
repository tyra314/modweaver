from setuptools import setup

setup(
    name="modweaver",
    version="1.0.0",
    license="GPLv3",
    description="A Minecraft mod manager for the command line.",
    author="tyra314 <tyra_oa@icloud.com>",
    url="https://github.com/tyra314/modweaver",
    python_requires=">=3.8",
    packages=["modweaver"],
    scripts=[],
    entry_points="""
      [console_scripts]
      modweaver=modweaver:main
      """,
    install_requires=[
        "aiofiles~=0.4.0",
        "aiohttp~=3.0",
        "click",
        "click-log",
        "click-completion",
        "semantic-version",
        "colorama",
        "toml",
        "dacite",
        "python-dateutil",
    ],
    project_urls={
        "Source": "https://github.com/tyra314/modweaver",
        "Bug Tracker": "https://github.com/tyra314/modweaver/issues",
    },
)
