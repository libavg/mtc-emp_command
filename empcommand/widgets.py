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
import random
from libavg import avg, Point2D

from empcommand import app

import engine
import consts


class GameWordsNode(avg.WordsNode):
    def __init__(self, parent=None, *args, **kwargs):
        kwargs['font'] = 'EMPRetro'
        kwargs['sensitive'] = False
        if 'fontsize' in kwargs:
            kwargs['fontsize'] = max(app().ynorm(kwargs['fontsize']), 7)
        super(GameWordsNode, self).__init__(*args, **kwargs)
        self.registerInstance(self,parent)


class VLayout(avg.DivNode):
    def __init__(self, interleave, width, parent=None, *args, **kwargs):
        super(VLayout, self).__init__(*args, **kwargs)
        self.registerInstance(self, parent)
        self.interleave = app().ynorm(interleave)
        self.size = Point2D(width, 1)
        self.yoffs = 0
        self.objs = []
    
    def add(self, obj, offset=0):
        self.appendChild(obj)
        self.objs.append(obj)
        obj.y = self.yoffs + offset
        if obj.size != Point2D(0, 0):
            objSize = obj.size
        else:
            objSize = obj.getMediaSize()
            
        self.yoffs += objSize.y + self.interleave + offset
        self.height = self.yoffs


class Tri(avg.DivNode):
    def __init__(self, parent=None, *args, **kwargs):
        super(Tri, self).__init__(*args, **kwargs)
        self.registerInstance(self,parent)

        self.pnode = avg.PolygonNode(
                pos=(
                    (self.width / 2, 0),
                    (0, self.height),
                    (self.width, self.height)
                ),
                opacity=0, fillcolor=consts.COLOR_RED, fillopacity=0.8, parent=self)


class MenuItem(avg.DivNode):
    SCROLL_SPEED = 0.8
    def __init__(self, text, width, cb, parent=None, *args, **kwargs):
        super(MenuItem, self).__init__(*args, **kwargs)
        self.registerInstance(self,parent)

        self.bg = avg.RectNode(opacity=0, fillopacity=0,
                fillcolor=consts.COLOR_BLUE, parent=self)

        self.wnode = GameWordsNode(text=text, fontsize=40, alignment='center',
                color=consts.COLOR_RED, parent=self)
        border = self.wnode.getMediaSize().y / 6
        self.wnode.y = border
        self.size = (width, self.wnode.getMediaSize().y + border * 2)
        self.bg.size = self.size
        self.wnode.x = width / 2
        self.cb = cb
        self.setEventHandler(avg.CURSORDOWN, avg.MOUSE | avg.TOUCH,
                lambda e: self.executeCallback())
        
        self.curContainer = avg.DivNode(sensitive=False, parent=self)
        avg.LineNode(pos1=(0, 0), pos2=(0, self.height), color=consts.COLOR_RED,
                strokewidth=3, parent=self.curContainer)
        
        self.__scrollSpeed = app().xnorm(self.SCROLL_SPEED * 100) / float(100)
        self.curState = 0

    def setActive(self, active):
        if active:
            self.bg.fillopacity = 0.2
            self.curContainer.opacity = 1
            self.curContainer.x = 0
        else:
            self.bg.fillopacity = 0
            self.curContainer.opacity = 0

    def update(self, dt):
        if self.curState == 0:
            self.curContainer.x += self.__scrollSpeed * dt
            if self.curContainer.x > self.width:
                self.curContainer.x = self.width
                self.curState = 1
        else:
            self.curContainer.x -= self.__scrollSpeed * dt
            if self.curContainer.x < 0:
                self.curContainer.x = 0
                self.curState = 0
            
    def executeCallback(self):
        engine.SoundManager.play('click.ogg')
        self.cb()


class DifficultyMenuItem(MenuItem):
    LABELS = ['Easy', 'Normal', 'Hard']
    def __init__(self, width, cb, *args, **kwargs):
        super(DifficultyMenuItem, self).__init__(text='X', width=width, cb=cb,
                *args, **kwargs)
        self.__lptr = 1
        self.__setText()
    
    def executeCallback(self):
        engine.SoundManager.play('click.ogg')
        self.__lptr = (self.__lptr + 1) % 3
        self.__setText()
        self.cb(self.__lptr)
    
    def __setText(self):
        self.wnode.text = self.LABELS[self.__lptr]
        

class Menu(avg.DivNode):
    def __init__(self, onPlay, onAbout, onDiffChanged, onQuit, parent=None, *args,  **kwargs):
        super(Menu, self).__init__(*args, **kwargs)
        self.registerInstance(self, parent)
        
        self.layout = VLayout(interleave=10, width=self.width, parent=self)
        self.layout.add(MenuItem(text='Play', width=self.width, cb=onPlay))
        self.layout.add(DifficultyMenuItem(width=self.width, cb=onDiffChanged))
        self.layout.add(MenuItem(text='About', width=self.width, cb=onAbout))
        self.layout.add(MenuItem(text='Quit', width=self.width, cb=onQuit))
        
        self.setActive(0, fb=False)
    
    def setActive(self, idx, fb=True):
        if idx == len(self.layout.objs) or idx < 0:
            return
            
        for ob in self.layout.objs:
            ob.setActive(False)
        
        self.layout.objs[idx].setActive(True)
        self.__active = idx
        
        if fb:
            engine.SoundManager.play('selection.ogg', volume=0.5)
    
    def update(self, dt):
        self.layout.objs[self.__active].update(dt)
        
    def onKeyDown(self, event):
        if event.keystring == 'down':
            self.setActive(self.__active + 1)
        elif event.keystring == 'up':
            self.setActive(self.__active - 1)
        elif event.keystring in ('return', 'space'):
            self.layout.objs[self.__active].executeCallback()
            

class HiscoreTab(avg.DivNode):
    SPEED_FACTOR = 20
    SMOOTH_FACTOR = 1.2
    MAX_SPEED = 6

    def __init__(self, db, parent=None, *args, **kwargs):
        super(HiscoreTab, self).__init__(*args, **kwargs)
        self.registerInstance(self, parent)
        self.db = db
        self.__nodes = []
        self.crop = True

        hdr = GameWordsNode(fontsize=20, text='HALL OF FAME', color=consts.COLOR_RED,
                width=self.width, pos=(self.width / 2, 0), alignment='center',
                parent=self)

        yp = hdr.getMediaSize().y + app().ynorm(5)
        avg.LineNode(pos1=(0, yp), pos2=(self.width, yp),
                strokewidth=1, color=consts.COLOR_BLUE, parent=self)

        self.__mask = avg.DivNode(parent=self, y=yp, crop=True)
        self.__stage = avg.DivNode(parent=self.__mask)

        self.__panningAnim = None

        self.__cursorid = None
        self.__initialTouchPos = None
        self.__lastYSpeed = 0
        self.__scrollLock = False
        self.__speedFactor = app().ynorm(self.SPEED_FACTOR)
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
            y = pos * app().ynorm(40)
            col1 = GameWordsNode(fontsize=20, text=self.toCardinal(pos + 1),
                    pos=app().pnorm((5, y + 4)), parent=self.__stage)
            col2 = GameWordsNode(fontsize=35, text=s.name,
                    pos=app().pnorm((75, y)),
                    color=consts.COLOR_BLUE, parent=self.__stage)
            col3 = GameWordsNode(fontsize=28, text=str(s.points), alignment='right',
                    color=consts.COLOR_RED,
                    pos=app().pnorm((345, y + 2)), parent=self.__stage)

            self.__nodes += [col1, col2, col3]
            pos += 1

        self.__stage.height = pos * app().ynorm(40)
        self.__stage.y = self.height

    def update(self, dt):
        if self.__cursorid is None and abs(self.__lastYSpeed) > 0.1:
            self.__stage.y += self.__lastYSpeed * self.__speedFactor
            self.__lastYSpeed /= self.SMOOTH_FACTOR
            self.__clampPan()
        elif not self.__scrollLock:
            self.__stage.y -= self.SMOOTH_FACTOR
            if self.__stage.y < -self.__stage.height:
                self.__stage.y = self.height

    def __clampPan(self):
        if self.__stage.y > self.height:
            self.__stage.y = self.height
        elif self.__stage.y < -self.__stage.height:
            self.__stage.y = -self.__stage.height

    def __onTouchDown(self, event):
        if self.__cursorid is None:
            self.__scrollLock = True
            self.setEventCapture(event.cursorid)
            self.__cursorid = event.cursorid
            self.__initialTouchPos = event.pos
            self.__lastYSpeed = 0

    def __onMotion(self, event):
        if self.__cursorid == event.cursorid:
            if abs(event.speed.y) > self.MAX_SPEED:
                self.__lastYSpeed = event.speed.y / event.speed.y * self.MAX_SPEED
            else:
                self.__lastYSpeed = event.speed.y
            self.__stage.y += event.speed.y * self.__speedFactor
            self.__clampPan()

    def __onTouchUp(self, event):
        if self.__cursorid == event.cursorid:
            self.releaseEventCapture(self.__cursorid)
            self.__cursorid = None
            self.__initialTouchPos = None
            self.__scrollLock = False


class Key(avg.DivNode):
    def __init__(self, char, cb, parent=None, *args, **kwargs):
        super(Key, self).__init__(*args, **kwargs)
        self.registerInstance(self, parent)
        self.__char = char
        self.__cb = cb
        self.__cursorid = None

        self.__bg = avg.RectNode(size=self.size, opacity=0, fillcolor=consts.COLOR_BLUE,
                fillopacity=1, parent=self)
        self.__wnode = GameWordsNode(pos=(self.width / 2 + app().xnorm(4),
                self.height / 2 - app().ynorm(28)),
                alignment='center', fontsize=50, color=consts.COLOR_RED,
                rawtextmode=True, parent=self)

        if char == '#':
            self.__wnode.text = 'OK'
            self.__wnode.fontsize = 30
            self.__wnode.y = self.height / 2 - app().ynorm(18)
        else:
            self.__wnode.text = char

        self.setEventHandler(avg.CURSORDOWN, avg.MOUSE | avg.TOUCH, self.__onTouchDown)
        self.setEventHandler(avg.CURSORUP, avg.MOUSE | avg.TOUCH, self.__onTouchUp)

    def __onTouchDown(self, event):
        if self.__cursorid is None:
            self.setEventCapture(event.cursorid)
            self.__cursorid = event.cursorid
            self.__bg.fillcolor = consts.COLOR_RED
            self.__wnode.color = consts.COLOR_BLUE

    def __onTouchUp(self, event):
        if self.__cursorid == event.cursorid:
            self.__bg.fillcolor = consts.COLOR_BLUE
            self.__wnode.color = consts.COLOR_RED
            self.__cursorid = None
            self.releaseEventCapture(event.cursorid)
            self.__cb(self.__char)


class Keyboard(avg.DivNode):
    def __init__(self, keySize, padding, cb, parent=None, *args, **kwargs):
        super(Keyboard, self).__init__(*args, **kwargs)
        self.registerInstance(self, parent)

        self.__cb = cb

        rows = [
            ['QWERTYUIOP<', 0],
            ['ASDFGHJKL#', (keySize + padding) / 2],
            ['ZXCVBNM ', keySize + padding]
        ]
        
        self.allowedKeys = []

        maxx = maxy = 0
        y = 0
        for r in rows:
            x = r[1]
            for c in r[0]:
                Key(c, self.__onKeyPressed, pos=(x, y), size=(keySize, keySize),
                        parent=self)
                self.allowedKeys.append(c)
                x += keySize + padding
                maxx = max(x, maxx)
            y += keySize + padding
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
    def __init__(self, parent=None, *args, **kwargs):
        super(PlayerName, self).__init__(*args, **kwargs)
        self.registerInstance(self, parent)

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

    def __init__(self, color, layout, parent=None, *args, **kwargs):
        super(Gauge, self).__init__(*args, **kwargs)
        self.registerInstance(self, parent)

        self.__layout = layout
        self.__levelContainer = avg.DivNode(parent=self)
        self.__level = avg.RectNode(size=self.size, opacity=0, fillopacity=1,
                fillcolor=color, parent=self.__levelContainer)
        avg.RectNode(size=self.size, color=color, strokewidth=1, 
                parent=self.__levelContainer)

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

    def setOpacity(self, opacity):
        self.__levelContainer.opacity = opacity

    def addLabel(self, text):
        GameWordsNode(text=text, alignment='center', fontsize=8, color='ffffff',
                pos=(self.size.x / 2, self.size.y + app().ynorm(5)),
                opacity=0.8, parent=self)


class CrossHair(avg.DivNode):
    NORMAL_COLOR = 'eeeeee'
    WARNING_COLOR = 'ff4444'
    
    warningy = -1
    
    def __init__(self, *args, **kwargs):
        super(CrossHair, self).__init__(*args, **kwargs)
        self.__l1 = avg.LineNode(pos1=(10, 0), pos2=(10, 20), strokewidth=4, parent=self)
        self.__l2 = avg.LineNode(pos1=(0, 10), pos2=(20, 10), strokewidth=4, parent=self)
        self.size = (20, 20)
    
    def refresh(self):
        if self.warningy > 0 and self.pos.y > self.warningy:
            self.__setWarning(True)
        else:
            self.__setWarning(False)
            
    def __setWarning(self, warning):
        if warning:
            self.__l1.color = self.__l2.color = self.WARNING_COLOR
        else:
            self.__l1.color = self.__l2.color = self.NORMAL_COLOR


class Clouds(avg.ImageNode):
    def __init__(self, maxOpacity, parent=None, *args, **kwargs):
        kwargs['href'] = 'clouds.png'
        super(Clouds, self).__init__(*args, **kwargs)
        self.registerInstance(self, parent)
        self.opacity = 0
        self.maxOpacity = maxOpacity
    
    def blink(self):
        def reset():
            avg.fadeOut(self, 180)
        avg.fadeIn(self, 80, random.uniform(0.05, self.maxOpacity), reset)


class RIImage(avg.ImageNode):
    def __init__(self, lock='x', parent=None, **kwargs):
        super(RIImage, self).__init__(**kwargs)
        self.registerInstance(self, parent)
        if lock == 'x':
            nf = app().xnorm
        else:
            nf = app().ynorm
        
        self.size = (nf(self.getMediaSize().x), nf(self.getMediaSize().y))


class ExitButton(avg.DivNode):
    UNSET_ICON_OPACITY = 0.3

    def __init__(self, parent=None, *args, **kwargs):
        super(ExitButton, self).__init__(*args, **kwargs)
        self.registerInstance(self, parent)

        self.__fill = RIImage(href='exit_fill.png', parent=self)
        self.__icon = RIImage(href='exit.png', parent=self)
        
    def activate(self, active):
        if active:
            self.opacity = 1
            self.__fill.opacity = 1
        else:
            self.opacity = self.UNSET_ICON_OPACITY
            self.__fill.opacity = 0


class QuitSwitch(avg.DivNode):
    BUTTON_RIGHT_XLIMIT = 148
    def __init__(self, cb, parent=None, *args, **kwargs):
        super(QuitSwitch, self).__init__(*args, **kwargs)
        self.registerInstance(self, parent)

        self.__slider = RIImage(href='exit_slider.png', parent=self)
        self.__button = ExitButton(parent=self)
        self.__buttonInitialPos = None
        self.__cursorId = None
        self.__anim = None
        self.__cb = cb
        self.__xlimit = app().xnorm(self.BUTTON_RIGHT_XLIMIT)
        
        self.__button.setEventHandler(avg.CURSORDOWN, avg.MOUSE | avg.TOUCH,
                self.__onDown)
        self.__button.setEventHandler(avg.CURSORUP, avg.MOUSE | avg.TOUCH, self.__onUp)
        self.__button.setEventHandler(avg.CURSORMOTION, avg.MOUSE | avg.TOUCH,
                self.__onMotion)
    
        self.reset()
        
    def reset(self):
        self.__button.pos = (self.__xlimit, 0)
        self.__slider.opacity = 0
        self.__button.activate(False)
        
    def __onDown(self, event):
        try:
            self.__button.setEventCapture(event.cursorid)
        except RuntimeError:
            pass
        else:
            self.__cursorId = event.cursorid
            self.__buttonInitialPos = event.pos - self.__button.pos
            self.__button.activate(True)
            avg.fadeIn(self.__slider, 100)
            
            return True
    
    def __onUp(self, event):
        if self.__cursorId is not None:
            self.__button.releaseEventCapture(event.cursorid)
            self.__cursorId = None
            
            self.__button.activate(False)
            
            if self.__button.x > 20:
                avg.fadeOut(self.__slider, 100)
                self.__anim = avg.EaseInOutAnim(self.__button, 'x', 200, self.__button.x,
                        self.__xlimit, 50, 150)
                self.__anim.start()
            else:
                self.__cb()
    
    def __onMotion(self, event):
        if self.__cursorId is not None:
            nx = (event.pos - self.__buttonInitialPos).x
            if nx < 0:
                nx = 0
            if nx > self.__xlimit:
                nx = self.__xlimit

            self.__button.x = nx
