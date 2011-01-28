#!/usr/bin/env python
# -*- coding: utf-8 -*-

# gameapp: common libavg MT games initialization / handling routines module
# Copyright (c) 2010-2011 OXullo Intersecans <x@brainrapers.org>. All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modification, are
# permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice, this list of
#    conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright notice, this list
#    of conditions and the following disclaimer in the documentation and/or other
#    materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY OXullo Intersecans ``AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
# FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL OXullo Intersecans OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# 
# The views and conclusions contained in the software and documentation are those of the
# authors and should not be interpreted as representing official policies, either 
# expressed or implied, of OXullo Intersecans.

import os
import sys
import libavg
from libavg import avg

g_Player = avg.Player.get()
g_Log = avg.Logger.get()

_app = None

def app():
    global _app
    return _app

class GameApp(libavg.AVGApp):
    multitouch = True

    def __init__(self, *args, **kwargs):
        avg.WordsNode.addFontDir(libavg.AVGAppUtil.getMediaDir(__file__, 'fonts'))
        global _app
        _app = self
        super(GameApp, self).__init__(*args, **kwargs)
        self._parentNode.mediadir = libavg.AVGAppUtil.getMediaDir(__file__)

    @classmethod
    def start(cls, *args, **kwargs):
        import optparse

        parser = optparse.OptionParser()
        parser.add_option('-r', '--resolution', dest='resolution',
                default=None, help='set an explicit resolution', metavar='WIDTHxHEIGHT')
        parser.add_option('-w', '--window', dest='window', action='store_true',
                default=False, help='run the game in a window')

        (options, args) = parser.parse_args()

        if options.resolution is not None:
            import re

            m = re.match('^(\d+)x(\d+)$', options.resolution)

            if m is None:
                sys.stderr.write('\n** ERROR: invalid resolution '
                        'specification %s\n\n' % options.resolution)
                parser.print_help()
                sys.exit(1)
            else:
                kwargs['resolution'] = map(int, m.groups())
        elif not 'resolution' in kwargs:
            kwargs['resolution'] = g_Player.getScreenResolution()

        if options.window:
            if options.resolution is None:
                sys.stderr.write('\n** ERROR: in window mode the resolution '
                        'must be set\n\n')
                parser.print_help()
                sys.exit(1)
            else:
                if 'AVG_DEPLOY' in os.environ:
                    del os.environ['AVG_DEPLOY']
        else:
            os.environ['AVG_DEPLOY'] = '1'

        g_Log.trace(g_Log.APP, 'Setting resolution to: %s' % kwargs['resolution'])

        super(GameApp, cls).start(*args, **kwargs)


    def getUserdataPath(self, fname):
        if os.name == 'posix':
            path = os.path.join(os.environ['HOME'], '.avg',
                    self.__class__.__name__.lower())
        elif os.name == 'nt':
            path = os.path.join(os.environ['APPDATA'], 'Avg',
                    self.__class__.__name__.lower())
        else:
            raise RuntimeError('Unsupported system %s' % os.name)

        try:
            os.makedirs(path)
        except OSError, e:
            import errno
            if e.errno != errno.EEXIST:
                raise

        return os.path.join(path, fname)
