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
import math
from libavg import avg, Point2D

import engine
import consts


class GameWordsNode(avg.WordsNode):
    def __init__(self, *args, **kwargs):
        kwargs['font'] = 'uni 05_53'
        kwargs['sensitive'] = False
        super(GameWordsNode, self).__init__(*args, **kwargs)


class Tri(avg.DivNode):
    def __init__(self, *args, **kwargs):
        super(Tri, self).__init__(*args, **kwargs)

        self.pnode = avg.PolygonNode(
                pos=(
                    (self.width / 2, 0),
                    (0, self.height),
                    (self.width, self.height)
                ),
                opacity=0, fillcolor=consts.COLOR_RED, fillopacity=0.8, parent=self)


class StartButton(avg.DivNode):
    WIDTH = 270
    HEIGHT = 270

    def __init__(self, *args, **kwargs):
        kwargs['size'] = (self.WIDTH, self.HEIGHT)
        super(StartButton, self).__init__(*args, **kwargs)

        GameWordsNode(text='Play', pos=(135, 110),
                fontsize=50, color=consts.COLOR_RED, alignment='center', parent=self)

        anims = []
        for i in xrange(32):
            tri = Tri(pos=(110, 215), size=(50, 50), opacity=i / 32.0, parent=self)
            tri.pivot = Point2D(25, -80)

            anims.append(avg.ContinuousAnim(tri, 'angle', math.pi / 16 * i, 2))

        self.__triAnim = avg.ParallelAnim(anims)

    def start(self):
        self.__triAnim.start()

    def stop(self):
        self.__triAnim.abort()


class HiscoreTab(avg.DivNode):
    SPEED_FACTOR = 20
    MAX_SPEED = 6
    WIDTH = 360
    HEIGHT = 300

    def __init__(self, db, *args, **kwargs):
        super(HiscoreTab, self).__init__(*args, **kwargs)
        self.db = db
        self.__nodes = []
        self.crop = True

        self.width = self.WIDTH
        self.height = self.HEIGHT

        GameWordsNode(fontsize=20, text='HALL OF FAME', color=consts.COLOR_RED,
                size=(self.width, 20),
                pos=(self.width / 2, 0), alignment='center', parent=self)
        avg.LineNode(pos1=(0, 20), pos2=(self.width, 20), strokewidth=1,
                color=consts.COLOR_BLUE, parent=self)

        self.__mask = avg.DivNode(parent=self, y=25, crop=True)
        self.__stage = avg.DivNode(parent=self.__mask)

        self.__panningAnim = None

        self.__capturedCursorId = None
        self.__initialTouchPos = None
        self.__lastYSpeed = 0
        self.__scrollLock = False
        self.setEventHandler(avg.CURSORDOWN, avg.MOUSE | avg.TOUCH, self.__onTouchDown)
        self.setEventHandler(avg.CURSORMOTION, avg.MOUSE | avg.TOUCH, self.__onMotion)
        self.setEventHandler(avg.CURSORUP, avg.MOUSE | avg.TOUCH, self.__onTouchUp)

    def toCardinal(self, num):
        if num % 10 == 1:
            return str(num) + 'st'
        elif num % 10 == 2:
            return str(num) + 'nd'
        elif num % 10 == 3:
            return str(num) + 'rd'
        else:
            return str(num) + 'th'

    def refresh(self):
        for n in self.__nodes:
            n.unlink(True)

        self.__nodes = []

        pos = 0
        for s in self.db.data:
            y = pos * 40
            col1 = GameWordsNode(fontsize=20, text=self.toCardinal(pos + 1),
                    pos=(5, y + 4), parent=self.__stage)
            col2 = GameWordsNode(fontsize=35, text=s.name, pos=(75, y),
                    color=consts.COLOR_BLUE, parent=self.__stage)
            col3 = GameWordsNode(fontsize=28, text=str(s.points), alignment='right',
                    color=consts.COLOR_RED,
                    pos=(345, y + 2), parent=self.__stage)

            self.__nodes += [col1, col2, col3]
            pos += 1

        self.__stage.height = pos * 40
        self.__stage.y = self.height

    def update(self, dt):
        if self.__capturedCursorId is None and abs(self.__lastYSpeed) > 0.1:
            self.__stage.y += self.__lastYSpeed * self.SPEED_FACTOR
            self.__lastYSpeed /= 1.2
            self.__clampPan()
        elif not self.__scrollLock:
            self.__stage.y -= 1.2
            if self.__stage.y < -self.__stage.height:
                self.__stage.y = self.height

    def __clampPan(self):
        if self.__stage.y > self.height:
            self.__stage.y = self.height
        elif self.__stage.y < -self.__stage.height:
            self.__stage.y = -self.__stage.height

    def __onTouchDown(self, event):
        if self.__capturedCursorId is None:
            self.__scrollLock = True
            self.setEventCapture(event.cursorid)
            self.__capturedCursorId = event.cursorid
            self.__initialTouchPos = event.pos
            self.__lastYSpeed = 0

    def __onMotion(self, event):
        if self.__capturedCursorId:
            if abs(event.speed.y) > self.MAX_SPEED:
                self.__lastYSpeed = event.speed.y / event.speed.y * self.MAX_SPEED
            else:
                self.__lastYSpeed = event.speed.y
            self.__stage.y += event.speed.y * self.SPEED_FACTOR
            self.__clampPan()

    def __onTouchUp(self, event):
        if self.__capturedCursorId:
            self.releaseEventCapture(self.__capturedCursorId)
            self.__capturedCursorId = None
            self.__initialTouchPos = None
            self.__scrollLock = False


class Key(avg.DivNode):
    def __init__(self, char, cb, *args, **kwargs):
        super(Key, self).__init__(*args, **kwargs)
        self.__char = char
        self.__cb = cb
        self.__capturedId = None

        self.__bg = avg.RectNode(size=self.size, opacity=0, fillcolor=consts.COLOR_BLUE,
                fillopacity=1, parent=self)
        self.__wnode = GameWordsNode(pos=(self.width / 2 + 4, self.height / 2 - 28),
                alignment='center', fontsize=50, color=consts.COLOR_RED,
                rawtextmode=True, parent=self)

        if char == '#':
            self.__wnode.text = 'OK'
            self.__wnode.fontsize = 30
            self.__wnode.y = self.height / 2 - 18
        else:
            self.__wnode.text = char

        self.setEventHandler(avg.CURSORDOWN, avg.MOUSE | avg.TOUCH, self.__onTouchDown)
        self.setEventHandler(avg.CURSORUP, avg.MOUSE | avg.TOUCH, self.__onTouchUp)

    def __onTouchDown(self, event):
        if self.__capturedId is None:
            self.setEventCapture(event.cursorid)
            self.__capturedId = event.cursorid
            self.__bg.fillcolor = consts.COLOR_RED
            self.__wnode.color = consts.COLOR_BLUE

    def __onTouchUp(self, event):
        if self.__capturedId == event.cursorid:
            self.__bg.fillcolor = consts.COLOR_BLUE
            self.__wnode.color = consts.COLOR_RED
            self.__capturedId = None
            self.releaseEventCapture(event.cursorid)
            self.__cb(self.__char)


class Keyboard(avg.DivNode):
    KEY_DIM = 60
    PADDING = 15
    def __init__(self, cb, *args, **kwargs):
        super(Keyboard, self).__init__(*args, **kwargs)

        self.__cb = cb

        rows = [
            ['QWERTYUIOP<', 0],
            ['ASDFGHJKL#', (self.KEY_DIM + self.PADDING) / 2],
            ['ZXCVBNM ', self.KEY_DIM + self.PADDING]
        ]

        maxx = maxy = 0
        y = 0
        for r in rows:
            x = r[1]
            for c in r[0]:
                Key(c, self.__onKeyPressed, pos=(x, y), size=(self.KEY_DIM, self.KEY_DIM),
                        parent=self)
                x += self.KEY_DIM + self.PADDING
                maxx = max(x, maxx)
            y += self.KEY_DIM + self.PADDING
            maxy = max(y, maxy)

        self.size = Point2D(maxx, maxy)

    def setEnabled(self, enabled):
        if enabled:
            avg.fadeIn(self, 1000)
            self.sensitive = True
        else:
            self.opacity = 0
            self.sensitive = False

    def __onKeyPressed(self, key):
        self.__cb(key)


class PlayerName(avg.DivNode):
    def __init__(self, *args, **kwargs):
        super(PlayerName, self).__init__(*args, **kwargs)
        self.size = Point2D(450, 150)

        self.__name = GameWordsNode(fontsize=150, color=consts.COLOR_RED, text='',
                alignment='center', pos=(self.size.x / 2, 0), parent=self)
        avg.LineNode(pos1=(0, self.size.y - 1), pos2=(self.size.x, self.size.y - 1),
                color=consts.COLOR_RED, strokewidth=2, parent=self)

    def reset(self):
        self.__name.text = ''

    def delete(self):
        if len(self.__name.text) > 0:
            self.__name.text = self.__name.text[0:len(self.__name.text) - 1]

    def addChar(self, ch):
        if len(self.__name.text) < 3:
            self.__name.text += ch

    @property
    def text(self):
        return self.__name.text


class Gauge(avg.DivNode):
    LAYOUT_VERTICAL = 'vertical'
    LAYOUT_HORIZONTAL = 'horizontal'

    def __init__(self, color, layout, *args, **kwargs):
        super(Gauge, self).__init__(*args, **kwargs)

        self.__layout = layout
        self.__level = avg.RectNode(size=self.size, opacity=0, fillopacity=1,
                fillcolor=color, parent=self)
        avg.RectNode(size=self.size, color='ffffff', strokewidth=0.5, parent=self)

        self.__fval = 0

    def getFVal(self):
        return self.__fval

    def setFVal(self, fv):
        if fv > 1:
            fv = 1
        elif fv < 0:
            fv = 0

        if self.__layout == self.LAYOUT_VERTICAL:
            self.__level.pos = Point2D(0, self.size.y * (1 - fv))
            self.__level.size = self.size - Point2D(0, self.__level.pos.y)
        elif self.__layout == self.LAYOUT_HORIZONTAL:
            self.__level.pos = Point2D(0, 0)
            self.__level.size = Point2D(self.size.x * fv, self.size.y)

        self.__fval = fv

    def setColor(self, color):
        self.__level.fillcolor = color


class CrossHair(avg.DivNode):
    def __init__(self, *args, **kwargs):
        super(CrossHair, self).__init__(*args, **kwargs)
        self.__l1 = avg.LineNode(pos1=(10, 0), pos2=(10, 20), strokewidth=4, parent=self)
        self.__l2 = avg.LineNode(pos1=(0, 10), pos2=(20, 10), strokewidth=4, parent=self)
        self.size = (20, 20)

