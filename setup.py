# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='pycytools',
    version='0.6.5',
    description='Helper functions to handle image cytometry data.',
    long_description=readme,
    author='Vito Zanotelli, Matthias Leutenegger, Bernd Bodenmiller',
    author_email='vito.zanotelli@gmail.com',
    url='https://github.com/bodenmillerlab/pycytools',
    license=license,
    packages=find_packages(exclude=('tests', 'docs')),
    install_requires = ['numpy',
                        'scipy',
                        'pandas',
                        'requests',
                        'scikit-image',
                        'tifffile'
                        ],
)

