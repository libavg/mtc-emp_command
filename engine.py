#!/usr/bin/env python
# -*- coding: utf-8 -*-

# engine module: generic game engine based on libavg, AVGApp
# Copyright (c) 2010 OXullo Intersecans <x@brainrapers.org>. All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modification, are
# permitted provided that the following conditions are met:
# 
#    1. Redistributions of source code must retain the above copyright notice, this list of
#       conditions and the following disclaimer.
# 
#    2. Redistributions in binary form must reproduce the above copyright notice, this list
#       of conditions and the following disclaimer in the documentation and/or other materials
#       provided with the distribution.
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
# authors and should not be interpreted as representing official policies, either expressed
# or implied, of OXullo Intersecans.

from libavg import avg, AVGApp

g_Player = avg.Player.get()
g_Log = avg.Logger.get()


class NotImplementedError(Exception):
    '''Method is not overloaded on child class'''

class EngineError(Exception):
    '''Generic engine error'''


class Singleton(type):
    '''
    Singleton metaclass
    
    U{http://bloop.sourceforge.net/wiki/index.php/Singleton_Metaclass}
    '''
    def __init__(cls,name,bases,dic):
        super(Singleton,cls).__init__(name,bases,dic)
        cls.instance=None
 
    def __call__(cls,*args,**kw):
        if cls.instance is None:
            cls.instance=super(Singleton,cls).__call__(*args,**kw)
        return cls.instance

class GameState(avg.DivNode):
    def __init__(self, *args, **kwargs):
        super(GameState, self).__init__(*args, **kwargs)
        self._isFrozen = False
        self._bgTrack = None
        self._maxBgTrackVolume = 1
        self.engine = None
        self.opacity = 0
    
    def registerEngine(self, engine):
        self.engine = engine
        self._init()
        
    def registerBgTrack(self, soundNode, maxVolume=1):
        self._bgTrack = soundNode
        self._bgTrack.volume = maxVolume
        self._maxBgTrackVolume = maxVolume

    def update(self, dt):
        self._update(dt)

    def onTouch(self, event):
        if not self._isFrozen:
            self._onTouch(event)

    def onKey(self, event):
        if not self._isFrozen:
            self._onKey(event)

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
    
    def _onKey(self, event):
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
        avg.LinearAnim(self._bgTrack, 'volume', self.TRANS_DURATION, self._maxBgTrackVolume
            , 0, False, None, self._bgTrack.stop).start()


class Engine(AVGApp):
    def __init__(self, *args, **kwargs):
        self.__registeredStates = {}
        self.__currentState = None
        self.__tickTimer = None
        self.__entryHandle = None
        self.__elapsedTime = 0
        super(Engine, self).__init__(*args, **kwargs)
    
    def registerState(self, handle, state):
        g_Log.trace(g_Log.APP, 'Registering state %s: %s' % (handle, state))
        state.registerEngine(self)
        self.__registeredStates[handle] = state
        self._parentNode.appendChild(state)
    
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
        g_Log.trace(g_Log.APP, 'Changing state %s -> %s' % (self.__currentState, newState))

        self.__currentState = newState
    
    def getState(self, handle):
        return self.__getState(handle)
            
    def onKey(self, event):
        if self.__currentState:
            self.__currentState.onKey(event)
    
    def onTouch(self, event):
        if self.__currentState:
            self.__currentState.onTouch(event)
    
    def _enter(self):
        self._parentNode.setEventHandler(avg.CURSORDOWN, avg.MOUSE | avg.TOUCH,
            self.onTouch)
        self.__tickTimer = g_Player.setOnFrameHandler(self.__onFrame)

        if self.__currentState:
            self.__currentState._resume()
        else:
            self.changeState(self.__entryHandle)
    
    def _leave(self):
        self._parentNode.setEventHandler(avg.CURSORDOWN, avg.MOUSE | avg.TOUCH,
            None)
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
        