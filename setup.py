#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name='EMPCommand',
    version='1.0',
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
