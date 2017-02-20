# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='pycytools',
    version='0.0.2',
    description='Tools to handle single cell data.',
    long_description=readme,
    author='Vito Zanotelli',
    author_email='vito.zanotelli@uzh.ch',
    url='https://github.com/bodenmillerlab/pycytools',
    license=license,
    packages=find_packages(exclude=('tests', 'docs')),
    install_requires = [
                       'tifffile', 'scikit-image', 'scikit-learn','numpy','pandas', 'scipy', 'requests', 'matplotlib', 'seaborn'],
)

