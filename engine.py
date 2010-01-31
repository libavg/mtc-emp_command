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

class GameState(avg.DivNode):
    def __init__(self, *args, **kwargs):
        super(GameState, self).__init__(*args, **kwargs)
        self._isFrozen = False
        self.engine = None
        self.opacity = 0
    
    def registerEngine(self, engine):
        self.engine = engine
        self._init()
        
    def update(self):
        self._update()

    def onTouch(self, event):
        if not self._isFrozen:
            self._onTouch(event)

    def onKey(self, event):
        if not self._isFrozen:
            self._onKey(event)

    def enter(self):
        self.opacity = 1
        self._enter()
    
    def leave(self):
        self._leave()
        self.opacity = 0
    
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
        
    def _update(self):
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
    
    def leave(self):
        self._isFrozen = True
        self._preTransOut()
        self._doTransOut(self.__postTransOut)
    
    def _doTransIn(self, postCb):
        raise NotImplementedError()
    
    def _doTransOut(self, postCb):
        raise NotImplementedError()
    
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


class Engine(AVGApp):
    def __init__(self, *args, **kwargs):
        self.__registeredStates = {}
        self.__currentState = None
        self.__tickTimer = None
        self.__entryHandle = None
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
        self.changeState(handle)
        
    def changeState(self, handle):
        if self.__entryHandle is None:
            raise EngineError('Game must be bootstrapped before changing its state')
        
        newState = self.__getState(handle)

        if self.__currentState:
            self.__currentState.leave()
            
        newState.enter()
        g_Log.trace(g_Log.APP, 'Changing state %s -> %s' % (self.__currentState, newState))

        self.__currentState = newState
    
    def proxyState(self, handle):
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
        self.__tickTimer = g_Player.setOnFrameHandler(self.__update)

        if self.__currentState:
            self.__currentState._resume()
    
    def _leave(self):
        self._parentNode.setEventHandler(avg.CURSORDOWN, avg.MOUSE | avg.TOUCH,
            None)
        g_Player.clearInterval(self.__tickTimer)
        self.__tickTimer = None
        
        if self.__currentState:
            self.__currentState._pause()
    
    def __getState(self, handle):
        if handle in self.__registeredStates:
            return self.__registeredStates[handle]
        else:
             EngineError('No state with handle %s' % handle)
        
    def __update(self):
        if self.__currentState:
            self.__currentState.update()
