#!/usr/bin/env python3

from setuptools import setup

description = 'A Selenium-less Python EgyBest Library'
__version__ = '2.2.0'

try:
	long_description = open('README.md', 'r').read()
except IOError:
	long_description = description

setup(
	name='egybest',
	version=__version__,
	packages=['egybest'],
	author='Safwan Ljd',
	license_files=('LICENSE',),
	description=description,
	long_description=long_description,
	long_description_content_type='text/markdown',
	python_requires='>=3.6',
	url='https://gitlab.com/SafwanLjd/PyEgyBest',
	download_url=f'https://gitlab.com/SafwanLjd/PyEgyBest/-/archive/v{__version__}/PyEgyBest-v{__version__}.tar.gz',
	install_requires=['js2py', 'bs4', 'requests', 'strsimpy'],
	classifiers=[
		'Development Status :: 5 - Production/Stable',
		'Intended Audience :: Developers',
		'Topic :: Software Development :: Build Tools',
		'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
		'Natural Language :: English',
		'Operating System :: OS Independent'
	]
)
