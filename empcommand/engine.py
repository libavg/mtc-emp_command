#!/usr/bin/env python
# -*- coding: utf-8 -*-

# engine module: generic game engine based on libavg, AVGApp
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
from libavg import avg, Point2D, gameapp, player

import consts


class NotImplementedError(Exception):
    '''Method is not overloaded on child class'''

class EngineError(Exception):
    '''Generic engine error'''


class SoundManager(object):
    objects = {}

    @classmethod
    def init(cls, parent):
        cls.parent = parent

    @classmethod
    def getSample(cls, fileName, loop=False):
        return avg.SoundNode(href=os.path.join('snd', fileName), loop=loop,
                parent=cls.parent)

    @classmethod
    def allocate(cls, fileName, nodes=1):
        if fileName in cls.objects:
            raise RuntimeError('Sound sample %s has been already allocated' % fileName)

        slst = []
        for i in xrange(0, nodes):
            s = SoundManager.getSample(fileName)
            slst.append(s)

        cls.objects[fileName] = slst

    @classmethod
    def play(cls, fileName, randomVolume=False, volume=None):
        if not fileName in cls.objects:
            raise RuntimeError('Sound sample %s hasn\'t been allocated' % fileName)

        mySound = cls.objects[fileName].pop(0)
        mySound.stop()

        if volume is not None:
            maxVol = volume
        else:
            maxVol = 1
            
        if randomVolume:
            mySound.volume = random.uniform(0.2, maxVol)
        elif volume is not None:
            mySound.volume = volume
        
        sc = mySound.play()

        cls.objects[fileName].append(mySound)


class ScoreEntry(object):
    def __init__(self, name, points):
        if type(points) not in (int, float):
            raise ValueError('Points must be expressed in int/float '
                    '(%s, %s)' % (points, type(points)))
        self.name = name
        self.points = points

    def __cmp__(self, other):
        if type(other) != ScoreEntry:
            raise TypeError('Cannot compare ScoreEntry with %s' %
                other.__class__.__name__)
        return cmp(self.points, other.points)

    def __repr__(self):
        return '<%s: name=%s points=%d>' % (self.__class__.__name__,
                self.name, self.points)


class HiscoreDatabase(object):
    def __init__(self, app, maxSize=20):
        self.__maxSize = maxSize
        self.__ds = app.initDatastore(tag='hiscore',
                initialData=self.__generateShit,
                validator=self.__validate)

    def isFull(self):
        return len(self.__ds.data) >= self.__maxSize

    def addScore(self, score, sync=True):
        self.__ds.data.append(score)
        self.__ds.data = sorted(self.__ds.data, reverse=True)[0:self.__maxSize]

        if sync:
            self.__ds.commit()

    @property
    def data(self):
        return self.__ds.data

    def __generateShit(self):
        import random
        data = []
        rng = 'QWERTYUIOPASDFGHJKLZXCVBNM'
        for i in xrange(self.__maxSize):
            data.append(
                    ScoreEntry(random.choice(rng) + \
                        random.choice(rng) + \
                        random.choice(rng),
                        random.randrange(80, 300) * 50))
        
        return sorted(data, reverse=True)

    def __validate(self, lst):
        if type(lst) != list or not lst:
            return False
        
        for se in lst:
            if not isinstance(se, ScoreEntry):
                return False
        
        return True

class GameState(avg.DivNode):
    def __init__(self, parent=None, **kwargs):
        super(GameState, self).__init__(**kwargs)
        self.registerInstance(self, parent)

        self._isFrozen = False
        self._bgTrack = None
        self._maxBgTrackVolume = 1
        self.engine = None
        self.opacity = 0
        self.sensitive = False

    def registerEngine(self, engine):
        self.engine = engine
        self._init()

    def registerBgTrack(self, fileName, maxVolume=1):
        self._bgTrack = SoundManager.getSample(fileName, loop=True)
        self._bgTrack.volume = maxVolume
        self._maxBgTrackVolume = maxVolume

    def update(self, dt):
        self._update(dt)

    def onTouch(self, event):
        if not self._isFrozen:
            self._onTouch(event)

    def onKeyDown(self, event):
        if not self._isFrozen:
            return self._onKeyDown(event)

    def onKeyUp(self, event):
        if not self._isFrozen:
            return self._onKeyUp(event)

    def enter(self):
        self.opacity = 1
        self._enter()
        self.sensitive = True
        if self._bgTrack:
            self._bgTrack.play()

    def leave(self):
        self.sensitive = False
        self._leave()
        self.opacity = 0
        if self._bgTrack:
            self._bgTrack.stop()

    def _init(self):
        pass

    def _enter(self):
        pass

    def _leave(self):
        pass

    def _pause(self):
        pass

    def _resume(self):
        pass

    def _update(self, dt):
        pass

    def _onTouch(self, event):
        pass

    def _onKeyDown(self, event):
        pass

    def _onKeyUp(self, event):
        pass


# Abstract
class TransitionGameState(GameState):
    TRANS_DURATION = 300
    def enter(self):
        self._isFrozen = True
        self._preTransIn()
        self._doTransIn(self.__postTransIn)
        if self._bgTrack:
            self._doBgTrackTransIn()

    def leave(self):
        self.sensitive = False
        self._isFrozen = True
        self._preTransOut()
        self._doTransOut(self.__postTransOut)
        if self._bgTrack:
            self._doBgTrackTransOut()

    def _doTransIn(self, postCb):
        raise NotImplementedError()

    def _doTransOut(self, postCb):
        raise NotImplementedError()

    def _doBgTrackTransIn(self):
        self._bgTrack.play()

    def _doBgTrackTransOut(self):
        self._bgTrack.stop()

    def _preTransIn(self):
        pass

    def _postTransIn(self):
        pass

    def _preTransOut(self):
        pass

    def _postTransOut(self):
        pass

    def __postTransIn(self):
        self._isFrozen = False
        self._postTransIn()
        self.sensitive = True

    def __postTransOut(self):
        self._isFrozen = False
        self._postTransOut()


class FadeGameState(TransitionGameState):
    def _doTransIn(self, postCb):
        avg.fadeIn(self, self.TRANS_DURATION, 1, postCb)

    def _doTransOut(self, postCb):
        avg.fadeOut(self, self.TRANS_DURATION, postCb)

    def _doBgTrackTransIn(self):
        self._bgTrack.volume = 0
        self._bgTrack.play()
        avg.LinearAnim(self._bgTrack, 'volume', self.TRANS_DURATION, 0,
                self._maxBgTrackVolume).start()

    def _doBgTrackTransOut(self):
        avg.LinearAnim(self._bgTrack, 'volume', self.TRANS_DURATION,
                self._maxBgTrackVolume, 0, False, None,
                self._bgTrack.stop).start()


class Application(gameapp.GameApp):
    def __init__(self, *args, **kwargs):
        self.__registeredStates = {}
        self.__currentState = None
        self.__tickTimer = None
        self.__entryHandle = None
        self.__elapsedTime = 0
        self.__pointer = None
        super(Application, self).__init__(*args, **kwargs)


    def setupPointer(self, instance):
        self._parentNode.appendChild(instance)
        instance.sensitive = False
        self.__pointer = instance
        player.showCursor(False)

    @property
    def size(self):
        return player.getRootNode().size

    def rnorm(self, value):
        return (value * math.sqrt((self.size.x ** 2 + self.size.y ** 2) /
                float(consts.ORIGINAL_SIZE[0] ** 2 + consts.ORIGINAL_SIZE[1] ** 2)))
        
    def xnorm(self, value):
        return int(value * self.size.x / float(consts.ORIGINAL_SIZE[0]))

    def ynorm(self, value):
        return int(value * self.size.y / float(consts.ORIGINAL_SIZE[1]))
    
    def pnorm(self, p, diagNorm=False):
        if len(p) == 2:
            point = Point2D(p)
        elif type(p) == Point2D:
            point = p
        else:
            raise ValueError('Cannot convert %s to Point2D' % str(args))
        
        if diagNorm:
            return Point2D(self.rnorm(point.x), self.rnorm(point.y))
        else:
            return Point2D(self.xnorm(point.x), self.ynorm(point.y))
    
    def spnorm(self, seq, diagNorm=False):
        nseq = []
        
        for p in seq:
            nseq.append(self.pnorm(p, diagNorm=diagNorm))
        
        return nseq
        
    def registerState(self, handle, state):
        avg.logger.trace(avg.logger.APP, 'Registering state %s: %s' % (handle, state))
        self._parentNode.appendChild(state)
        state.registerEngine(self)
        self.__registeredStates[handle] = state

    def bootstrap(self, handle):
        if self.__currentState:
            raise EngineError('The game has been already bootstrapped')

        self.__entryHandle = handle

    def changeState(self, handle):
        if self.__entryHandle is None:
            raise EngineError('Game must be bootstrapped before changing its state')

        newState = self.__getState(handle)

        if self.__currentState:
            self.__currentState.leave()

        newState.enter()
        avg.logger.trace(avg.logger.APP, 'Changing state %s -> %s' % (self.__currentState,
                newState))

        self.__currentState = newState

    def getState(self, handle):
        return self.__getState(handle)

    def onKeyDown(self, event):
        if self.__currentState:
            return self.__currentState.onKeyDown(event)

    def onKeyUp(self, event):
        if self.__currentState:
            return self.__currentState.onKeyUp(event)

    def onTouch(self, event):
        if self.__currentState:
            self.__currentState.onTouch(event)

        if event.source == avg.TOUCH and self.__pointer:
            self.__pointer.opacity = 0

    def onMouseMotion(self, event):
        if self.__pointer:
            self.__pointer.opacity = 1
            self.__pointer.pos = event.pos - self.__pointer.size / 2
            self.__pointer.refresh()

    def _enter(self):
        self._parentNode.subscribe(avg.Node.CURSOR_DOWN, self.onTouch)
        self._parentNode.subscribe(avg.Node.CURSOR_MOTION, self.onMouseMotion)

        self.__tickTimer = player.setOnFrameHandler(self.__onFrame)

        if self.__currentState:
            self.__currentState._resume()
        else:
            self.changeState(self.__entryHandle)

    def _leave(self):
        self._parentNode.unsubscribe(avg.Node.CURSOR_DOWN, self.onTouch)
        self._parentNode.unsubscribe(avg.Node.CURSOR_MOTION, self.onMouseMotion)
        player.clearInterval(self.__tickTimer)
        self.__tickTimer = None

        if self.__currentState:
            self.__currentState.leave()
            self.__currentState = None

    def _getPackagePath(self):
        return __file__
        
    def __getState(self, handle):
        if handle in self.__registeredStates:
            return self.__registeredStates[handle]
        else:
             raise EngineError('No state with handle %s' % handle)

    def __onFrame(self):
        if self.__currentState:
            dt = player.getFrameTime() - self.__elapsedTime
            self.__currentState.update(dt)

        self.__elapsedTime = player.getFrameTime()
