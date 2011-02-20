#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils.core import setup
from empcommand import VERSION

setup(
    name='EMPCommand',
    version=VERSION,
    author='OXullo Intersecans',
    author_email='x@brainrapers.org',
    url='http://www.brainrapers.org/empcommand/',
    license='BSD',
    packages=['empcommand'],
    scripts=['scripts/empcommand'],
    package_data={
            'empcommand': ['media/*.png', 'media/snd/*.ogg', 'fonts/*.ttf'],
    }
)

