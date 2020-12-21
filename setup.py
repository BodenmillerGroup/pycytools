# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('README.rst') as f:
    readme = f.read()

setup(
    name='pycytools',
    version='0.9.0',
    description='Helper functions to handle image cytometry data.',
    long_description=readme,
    long_description_content_type='text/x-rst',
    author='Vito Zanotelli, Matthias Leutenegger, Bodenmiller Lab UZH',
    author_email='vito.zanotelli@gmail.com',
    url='https://github.com/BodenmillerGroup/pycytools',
    license='BSD-3 License',
    packages=find_packages(exclude=('tests', 'docs')),
    install_requires=['numpy',
                      'scipy',
                        'pandas',
                        'requests',
                        'scikit-image',
                        'tifffile'
                        ],
)

