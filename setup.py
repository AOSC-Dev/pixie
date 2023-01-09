#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

from pixie import __version__

with open('README.md', 'r') as fh:
    long_description = fh.read()

setup(
    name="pixie",
    version=f'0.1.{__version__}',
    author='RedL0tus',
    author_email='kaymw@aosc.io',
    description='Dependency scanner of ELF executables',
    license='GNU Lesser General Public License v2 (LGPLv2)',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/AOSC-Dev/pixie',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 3',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)',  # noqa: E501
        'Operating System :: POSIX :: Linux',
    ],
    python_requires='>=3.10',
    scripts=['pscan']
)
