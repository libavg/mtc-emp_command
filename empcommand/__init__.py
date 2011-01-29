#!/usr/bin/env python
# -*- coding: utf-8 -*-

# EMP Command: a missile command multitouch clone
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
from libavg import avg, AVGApp, Point2D, AVGAppUtil

import engine
import states
import widgets
import consts

from gameapp import app

g_Player = avg.Player.get()
g_Log = avg.Logger.get()

__all__ = ['apps', 'EmpCommand']


class EmpCommand(engine.Application):
    exitButton = True

    def init(self):
        if engine.USE_PYGAME_MIXER:
            g_Log.trace(g_Log.APP, 'Using pygame.mixer for audio FX')
        else:
            g_Log.trace(g_Log.APP, 'Using libavg sound nodes for audio FX')

        engine.SoundManager.init(self._parentNode)

        avg.RectNode(fillopacity=1, fillcolor='000000', opacity=0,
                size=self.size, parent=self._parentNode)

        self.scoreDatabase = engine.HiscoreDatabase(consts.HISCORE_FILENAME)

        engine.SoundManager.allocate('bonus_alert.ogg')
        engine.SoundManager.allocate('bonus_drop.ogg')
        engine.SoundManager.allocate('click.ogg')
        engine.SoundManager.allocate('emp.ogg', 5)
        engine.SoundManager.allocate('enemy_exp1.ogg', 2)
        engine.SoundManager.allocate('enemy_exp2.ogg', 2)
        engine.SoundManager.allocate('enemy_exp3.ogg', 2)
        engine.SoundManager.allocate('enemy_exp4.ogg', 2)
        engine.SoundManager.allocate('enemy_exp5.ogg', 2)
        engine.SoundManager.allocate('low_ammo.ogg')
        engine.SoundManager.allocate('missile_launch.ogg', 5)
        engine.SoundManager.allocate('nuke.ogg')
        engine.SoundManager.allocate('nuke_launch.ogg')
        engine.SoundManager.allocate('target_destroy.ogg', 5)
        engine.SoundManager.allocate('target_hit.ogg')

        self.registerState('start', states.Start())
        self.registerState('about', states.About())
        self.registerState('game', states.Game())
        self.registerState('gameover', states.GameOver())
        self.registerState('results', states.Results())
        self.registerState('hiscore', states.Hiscore())

        self.setupPointer(widgets.CrossHair())
        self.bootstrap('start')


def createPreviewNode(maxSize):
    filename = os.path.join(AVGAppUtil.getMediaDir(__file__), 'preview.png')

    return AVGAppUtilcreateImagePreviewNode(maxSize, absHref = filename)

apps = (
        {'class': EmpCommand,
            'createPreviewNode': createPreviewNode},
        )

