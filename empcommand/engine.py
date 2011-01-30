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
import pickle
import random
import atexit
from libavg import avg
import gameapp
import consts

USE_PYGAME_MIXER = consts.SOUND_PYGAME

if USE_PYGAME_MIXER:
    try:
        import pygame.mixer
        pygame.mixer.init(frequency=consts.SOUND_FREQUENCY,
                buffer=consts.SOUND_BUFFER_SIZE)
        pygame.mixer.set_num_channels(consts.SOUND_VOICES)
    except ImportError:
        USE_PYGAME_MIXER = False


g_Player = avg.Player.get()
g_Log = avg.Logger.get()


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
        if USE_PYGAME_MIXER:
            base = os.path.dirname(os.path.abspath(__file__))
            return pygame.mixer.Sound(os.path.join(base, 'media', 'snd', fileName))
        else:
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
        if not USE_PYGAME_MIXER:
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

        if USE_PYGAME_MIXER and sc is None:
            g_Log.trace(g_Log.WARNING, 'Sound allocation failed: %s' % mySound)

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
    PICKLE_PROTO = 0

    def __init__(self, dataFile, maxSize=20):
        dataFile = gameapp.app().getUserdataPath(dataFile)
        self.__dataFile = dataFile
        self.__data = []
        self.__maxSize = maxSize
        atexit.register(self.__dump)

        g_Log.trace(g_Log.APP, 'Initializing hiscore database %s' % dataFile)

        if not self.__load(dataFile):
            if os.path.exists(dataFile + '.bak'):
                if self.__load(dataFile + '.bak'):
                    g_Log.trace(g_Log.WARNING,
                            'Hiscore data file is unreadable, using backup')
                else:
                    g_Log.trace(g_Log.ERROR,
                            'Cannot recover hiscore data, starting from scratch')
                    self.fillShit()
            else:
                    g_Log.trace(g_Log.ERROR,
                            'Cannot recover hiscore data, starting from scratch')
                    self.fillShit()
        elif not os.path.exists(dataFile):
            g_Log.trace(g_Log.WARNING, 'Hiscore data unavailable, generating '
                    'random scores')
            self.fillShit()

    def isFull(self):
        return len(self.__data) >= self.__maxSize

    def addScore(self, score, sync=True):
        self.__data.append(score)
        self.__data = sorted(self.__data, reverse=True)

        if sync:
            self.__dump()

    @property
    def data(self):
        return self.__data

    def fillShit(self):
        import random
        rng = 'QWERTZUIOPASDFGHJKLYXCVBNM'
        for i in xrange(self.__maxSize):
            self.addScore(ScoreEntry(random.choice(rng) + \
                    random.choice(rng) + \
                    random.choice(rng),
                    random.randrange(80, 300) * 50), sync=False)

    def __load(self, fileName):
        try:
            f = open(fileName)
        except IOError:
            return False

        try:
            self.__data = pickle.load(f)
        except:
            f.close()
            return False

        f.close()

        if len(self.__data) == 0:
            return False
        elif len(self.__data) > self.__maxSize:
            g_Log.trace(g_Log.WARNING, 'Slicing score data, trashing %d records' % (
                    len(self.__data) - self.__maxSize))
            self.__data = self.__data[0:self.__maxSize]

        return True

    def __dump(self):
        if os.path.exists(self.__dataFile):
            try:
                os.rename(self.__dataFile, self.__dataFile + '.bak')
            except OSError:
                g_Log.trace(g_Log.WARNING, 'Cannot create hiscores backup')

        try:
            f = open(self.__dataFile, 'wb')
        except IOError:
            g_Log.trace(g_Log.ERROR, 'Cannot safely save hiscores')
            return

        pickle.dump(self.__data, f, self.PICKLE_PROTO)
        f.close()
        g_Log.trace(g_Log.APP, 'Hiscore database dumped to %s' % self.__dataFile)


class GameState(avg.DivNode):
    def __init__(self, *args, **kwargs):
        super(GameState, self).__init__(*args, **kwargs)
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
        if USE_PYGAME_MIXER:
            self._bgTrack.set_volume(maxVolume)
        else:
            self._bgTrack.volume = maxVolume
        self._maxBgTrackVolume = maxVolume

    def update(self, dt):
        self._update(dt)

    def onTouch(self, event):
        if not self._isFrozen:
            self._onTouch(event)

    def onKeyDown(self, event):
        if not self._isFrozen:
            self._onKeyDown(event)

    def onKeyUp(self, event):
        if not self._isFrozen:
            self._onKeyUp(event)

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
        if USE_PYGAME_MIXER:
            self._bgTrack.play(loops= -1, fade_ms=self.TRANS_DURATION)
        else:
            self._bgTrack.volume = 0
            self._bgTrack.play()
            avg.LinearAnim(self._bgTrack, 'volume', self.TRANS_DURATION, 0,
                    self._maxBgTrackVolume).start()

    def _doBgTrackTransOut(self):
        if USE_PYGAME_MIXER:
            self._bgTrack.fadeout(self.TRANS_DURATION)
        else:
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
        g_Player.showCursor(False)

    @property
    def size(self):
        return g_Player.getRootNode().size

    def xnorm(self, value):
        return int(value * self.size.x / float(consts.ORIGINAL_SIZE[0]))

    def ynorm(self, value):
        return int(value * self.size.y / float(consts.ORIGINAL_SIZE[1]))
        
    def registerState(self, handle, state):
        g_Log.trace(g_Log.APP, 'Registering state %s: %s' % (handle, state))
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
        g_Log.trace(g_Log.APP, 'Changing state %s -> %s' % (self.__currentState,
                newState))

        self.__currentState = newState

    def quit(self):
        if gameapp.ownStarter:
            g_Player.stop()
        else:
            self.leave()
        
    def getState(self, handle):
        return self.__getState(handle)

    def onKeyDown(self, event):
        if self.__currentState:
            self.__currentState.onKeyDown(event)

    def onKeyUp(self, event):
        if self.__currentState:
            self.__currentState.onKeyUp(event)

    def onTouch(self, event):
        if self.__currentState:
            self.__currentState.onTouch(event)

        if event.source == avg.TOUCH and self.__pointer:
            self.__pointer.opacity = 0

    def onMouseMotion(self, event):
        if self.__pointer:
            self.__pointer.opacity = 1
            self.__pointer.pos = event.pos - self.__pointer.size / 2

    def _enter(self):
        self._parentNode.setEventHandler(avg.CURSORDOWN, avg.MOUSE | avg.TOUCH,
                self.onTouch)
        self._parentNode.setEventHandler(avg.CURSORMOTION, avg.MOUSE,
                self.onMouseMotion)

        self.__tickTimer = g_Player.setOnFrameHandler(self.__onFrame)

        if self.__currentState:
            self.__currentState._resume()
        else:
            self.changeState(self.__entryHandle)

    def _leave(self):
        self._parentNode.setEventHandler(avg.CURSORDOWN,
                avg.MOUSE | avg.TOUCH, None)
        self._parentNode.setEventHandler(avg.CURSORMOTION,
                avg.MOUSE, None)
        g_Player.clearInterval(self.__tickTimer)
        self.__tickTimer = None

        if self.__currentState:
            self.__currentState.leave()
            self.__currentState = None

    def __getState(self, handle):
        if handle in self.__registeredStates:
            return self.__registeredStates[handle]
        else:
             raise EngineError('No state with handle %s' % handle)

    def __onFrame(self):
        if self.__currentState:
            self.__currentState.update(g_Player.getFrameTime() - self.__elapsedTime)

        self.__elapsedTime = g_Player.getFrameTime()
