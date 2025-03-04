"""Template arguments:

- pkg_name: Python package name, default if mypkg
- exe_name: Executable name for the GUI app, default is myApp

"""
from setuptools import setup


PKG_NAME = "dm.wfdata"


install_requires = [
    "pandas>=1.5,<2.0",
    "numpy>=1.24,<2.0",
    "scipy>=1.10,<2.0",
    "matplotlib>=3.6,<3.7",
    "tables>=3.7,<4.0",
    "openpyxl>=3.0,<3.2",
]


def set_entry_points():
    r = {}
    r['gui_scripts'] = [
        f'dm-wave={PKG_NAME}.wave:main',
    ]
    return r


def readme():
    with open('README.md', 'r') as f:
        return f.read()


def read_license():
    with open('LICENSE') as f:
        return f.read()


setup(
    name=f'{PKG_NAME}',
    version='0.8.2',
    description='Tools for Managing the post-mortem BPM/BCM waveform data',
    long_description=readme(),
    license=read_license(),
    author="Tong Zhang",
    author_email="zhangt@frib.msu.edu",
    url="https://stash.frib.msu.edu/projects/PHYAPP/repos/phantasy-apps",
    packages=[
        f'{PKG_NAME}.wave',
        f'{PKG_NAME}'
    ],
    package_dir={
        f'{PKG_NAME}.wave': 'src/wave',
        f'{PKG_NAME}': 'src',
    },
    entry_points=set_entry_points(),
    install_requires=install_requires,
    include_package_data=True
)
