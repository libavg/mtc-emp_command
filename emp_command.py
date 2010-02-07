#!/usr/bin/env python
# -*- coding: utf-8 -*-

# EMP Command: a missile command multitouch clone
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


import os
import math
import random
from libavg import avg, AVGApp, Point2D, AVGAppUtil
import engine

g_Player = avg.Player.get()
g_Log = avg.Logger.get()

COLOR_BLUE = '0000ff'
COLOR_RED = 'ff0000'
ENEMY_FULLSPEED_Y = 300
GAMEOVER_DELAY = 4000
RESULTS_ADDROW_DELAY = 1000
RESULTS_DELAY = 3000
SLOT_WIDTH = 100
ENEMIES_WAVE_MULT = 25
AMMO_WAVE_MULT = 20
GREAT_HITS = 3
NUKE_HITS = 4
TURRETS_AMOUNT = 3
ULTRASPEED_MISSILE_MUL = 7
DELTAT_NORM_FACTOR = 17

RESOLUTION = Point2D(1280, 800)

INVALID_TARGET_Y_OFFSET = 100

CITY_RESCUE_SCORE = 800
ENEMY_DESTROYED_SCORE = 50

DEBUG = 'EMP_DEBUG' in os.environ

def sqdist(p1, p2):
    pd = p1 - p2
    return pd.x ** 2 + pd.y ** 2


class LayeredSprite(object):
    layer = None
    
    @classmethod
    def initLayer(cls, parent):
        cls.layer = avg.DivNode(parent=parent)


class Explosion(LayeredSprite):
    objects = []
    
    def __init__(self, pos):
        self._node = avg.CircleNode(pos=pos, r=20, fillcolor=self.COLOR,
            opacity=0, fillopacity=1, parent=self.layer)
        
        diman = avg.LinearAnim(self._node, 'r', self.DURATION, 1, self.RADIUS)
        opaan = avg.LinearAnim(self._node, 'fillopacity', self.DURATION, 1, 0)
        self.__anim = avg.ParallelAnim((diman, opaan), None, self._cleanup)
        self.__anim.start()
        self.objects.append(self)
    
    def _cleanup(self):
        self.__anim.abort()
        del self.__anim
        self._node.unlink()
        self.objects.remove(self)

    @classmethod
    def filter(cls, subClass):
        return [t for t in cls.objects if isinstance(t, subClass)]
    
class AllyExplosion(Explosion):
    DURATION = 500
    RADIUS = 60
    COLOR = COLOR_BLUE
    
    def __init__(self, pos):
        self.hits = 0
        super(AllyExplosion, self).__init__(pos)

    def addHit(self):
        self.hits += 1
    
    def _cleanup(self):
        if self.hits == GREAT_HITS:
            AmmoBonus(self._node.pos, 10000)
        elif self.hits == NUKE_HITS:
            NukeBonus(self._node.pos, 20000)
        
        super(AllyExplosion, self)._cleanup()
        

class NukeExplosion(AllyExplosion):
    DURATION = 2500
    RADIUS = 600

    def addHit(self):
        pass

class EnemyExplosion(Explosion):
    DURATION = 1000
    RADIUS = 40
    COLOR = COLOR_RED


class TouchFeedback(LayeredSprite):
    def __init__(self, pos, color):
        self.__node = avg.CircleNode(color=color, strokewidth=2,
            parent=self.layer, r=10, pos=pos)
        
        diman = avg.LinearAnim(self.__node, 'r', 200, 10, 20)
        opaan = avg.LinearAnim(self.__node, 'opacity', 200, 1, 0)
        self.__anim = avg.ParallelAnim((diman, opaan), None, self.__cleanup)
        self.__anim.start()
    
    def __cleanup(self):
        del self.__anim
        self.__node.unlink()

class TextFeedback(LayeredSprite):
    TRANSITION_TIME = 500
    def __init__(self, pos, text, color):
        self.__node = GameWordsNode(text=text,
            parent=self.layer, pos=pos, fontsize=30, color=color, alignment='center')

        diman = avg.LinearAnim(self.__node, 'fontsize', self.TRANSITION_TIME, 30, 60)
        opaan = avg.LinearAnim(self.__node, 'opacity', self.TRANSITION_TIME, 1, 0)
        offsan = avg.LinearAnim(self.__node, 'pos',
            self.TRANSITION_TIME, pos, pos - Point2D(70, 70))
        self.__anim = avg.ParallelAnim((diman, opaan, offsan), None, self.__cleanup)
        self.__anim.start()
    
    def __cleanup(self):
        del self.__anim
        self.__node.unlink()


class Bonus(LayeredSprite):
    TRANSITION_TIME = 200
    OPACITY = 0.6
    TRANSITION_ZOOM = 12
    DROP_RADIUS_SQ = 900
    
    spawnTimestamp = {}
    
    def __init__(self, pos, icon, waitTime):
        if (self.__class__ in self.spawnTimestamp and
            g_Player.getFrameTime() - self.spawnTimestamp[self.__class__] < waitTime):
                return
        else:
            self.spawnTimestamp[self.__class__] = g_Player.getFrameTime()
        
        self._node = avg.ImageNode(href=icon, pos=pos, parent=self.layer)
        diman = avg.LinearAnim(self._node, 'size', self.TRANSITION_TIME,
            self._node.getMediaSize() * self.TRANSITION_ZOOM,
            self._node.getMediaSize())
        opaan = avg.LinearAnim(self._node, 'opacity', self.TRANSITION_TIME, 0, self.OPACITY)
        offsan = avg.LinearAnim(self._node, 'pos', self.TRANSITION_TIME,
            Point2D(pos) - self._node.getMediaSize() * self.TRANSITION_ZOOM / 2, pos)
        self._anim = avg.ParallelAnim((diman, opaan, offsan), None, self.__ready)
        self._anim.start()
        

    def _trigger(self):
        return False
    
    def _suckIn(self, pos, callback):
        diman = avg.LinearAnim(self._node, 'size', self.TRANSITION_TIME,
            self._node.size, Point2D(1,1))
        opaan = avg.LinearAnim(self._node, 'opacity', self.TRANSITION_TIME,
            self.OPACITY, 0)
        offsan = avg.LinearAnim(self._node, 'pos', self.TRANSITION_TIME,
            self._node.pos, pos)
        self._anim = avg.ParallelAnim((diman, opaan, offsan), None,
            callback)
        self._anim.start()
        
    def __move(self, event):
        self._node.pos = event.pos - self.__handlePos
        
    def __release(self, event):
        self._node.setEventHandler(avg.CURSORMOTION, avg.MOUSE | avg.TOUCH,
            None)
        self._node.setEventHandler(avg.CURSORUP, avg.MOUSE | avg.TOUCH,
            None)
        self._node.releaseEventCapture(self.__cursorid)
        
        if not self._trigger():
            self.__disappear()
        
    def __startDrag(self, event):
        self._node.setEventHandler(avg.CURSORUP, avg.MOUSE | avg.TOUCH,
            self.__release)
        self._node.setEventHandler(avg.CURSORMOTION, avg.MOUSE | avg.TOUCH,
            self.__move)
        self._node.setEventCapture(event.cursorid)
        self.__cursorid = event.cursorid
        self.__handlePos = event.pos - self._node.pos
        
        self._anim.setStopCallback(None)
        self._anim.abort()
        self._node.opacity = self.OPACITY
        
        return True
    
    def __ready(self):
        self._node.setEventHandler(avg.CURSORDOWN, avg.MOUSE | avg.TOUCH,
            self.__startDrag)
        
        self.__disappear()
        
    def __disappear(self):
        self._anim = avg.fadeOut(self._node, 3000, self._destroy)
    
    def _destroy(self):
        del self._anim
        self._node.unlink(True)

class NukeBonus(Bonus):
    def __init__(self, pos, waitTime=0):
        super(NukeBonus, self).__init__(pos, 'bns_nuke.png', waitTime)
        self.__targetTurret = None
    
    def _trigger(self):
        def loadNuke():
            self.__turret.loadNuke()
            self._destroy()
            
        for t in Target.filter(Turret):
            if (sqdist(self._node.pos + self._node.size / 2,
                t.getHitPos()) < self.DROP_RADIUS_SQ):
                    self.__turret = t
                    self._suckIn(t.getHitPos(), loadNuke)
                    return True
                    
        
class AmmoBonus(Bonus):
    def __init__(self, pos, waitTime=0):
        super(AmmoBonus, self).__init__(pos, 'bns_ammo.png', waitTime)

    def _trigger(self):
        def loadAmmo():
            self.__turret.rechargeAmmo()
            self._destroy()
            
        for t in Target.filter(Turret):
            if (sqdist(self._node.pos + self._node.size / 2,
                t.getHitPos()) < self.DROP_RADIUS_SQ):
                    self.__turret = t
                    self._suckIn(t.getHitPos(), loadAmmo)
                    return True
        
# Abstract
class Missile(LayeredSprite):
    objects = []
    speedMul = 1
    TRAIL_THICKNESS = 1
    def __init__(self, initPoint, targetPoint):
        self.initPoint = initPoint
        self.targetPoint = targetPoint
        self.__isExploding = False
            
        self.traj = avg.LineNode(pos1=self.initPoint, pos2=self.initPoint,
            color=self.COLOR, strokewidth=self.TRAIL_THICKNESS, parent=self.layer)

        self.nominalSpeedVec = ((self.targetPoint - self.initPoint).getNormalized() * 
            random.uniform(*self.speedRange) / DELTAT_NORM_FACTOR)
        self.__fade = None
        self.objects.append(self)
    
    def explode(self):
        if not self.__isExploding:
            self.__isExploding = True
            self.__fade = avg.fadeOut(
                self.traj, self.explosionClass.DURATION / 2, self.__cleanup)
            self.explosionClass(self.traj.pos2)
    
    def destroy(self):
        if self.__fade:
            self.__fade.abort()
        
        self.__cleanup()

    def collisionCheck(self, dt):
        pass
    
    def getSpeedFactor(self):
        return 1
    
    def speedVector(self, dt):
        return (
                self.nominalSpeedVec *
                self.getSpeedFactor() *
                self.speedMul *
                dt
            )
            
    def __cleanup(self):
        del self.__fade
        self.traj.unlink()
        self.objects.remove(self)

    def __repr__(self):
        return '%s %s -> (%d, %d)' % (self.__class__.__name__, self.initPoint,
            int(self.traj.pos2.x), int(self.traj.pos2.y))
        
    @classmethod
    def filter(cls, subClass):
        return [t for t in cls.objects if isinstance(t, subClass)]
        
    @classmethod
    def update(cls, dt):
        for m in cls.objects:
            if not m.__isExploding:
                m.traj.pos2 += m.speedVector(dt)
                m.collisionCheck(dt)

class Enemy(Missile):
    speedRange = [0.5, 1]
    explosionClass = EnemyExplosion
    COLOR = COLOR_RED
    
    def __init__(self, initPoint, targetObj, level):
        self.__level = level
        # TODO: dangling reference
        self.__targetObj = targetObj
        super(Enemy, self).__init__(initPoint, targetObj.getHitPos())
        
    def collisionCheck(self, dt):
        # Check if the enemy enters an EMP shockwave
        for exp in Explosion.filter(AllyExplosion):
            if sqdist(exp._node.pos, self.traj.pos2) < exp._node.r ** 2:
                    exp.addHit()
                    if exp.hits == GREAT_HITS:
                        TextFeedback(exp._node.pos, 'GREAT!', COLOR_BLUE)
                    elif exp.hits == NUKE_HITS:
                        TextFeedback(exp._node.pos, '** AWESOME **', COLOR_BLUE)
                    self.explode()
                    EmpCommand().getState('game').enemyDestroyed(self)

        # Check if the enemy reached its destination
        v = self.speedVector(dt)
        if sqdist(self.traj.pos2, self.targetPoint) <= (v.x ** 2 + v.y ** 2):
            self.explode()
            EmpCommand().getState('game').enemyDestroyed(self, self.__targetObj)
        

    def getSpeedFactor(self):
        if self.traj.pos2.y < ENEMY_FULLSPEED_Y:
            myspeed =  float(self.traj.pos2.y) / ENEMY_FULLSPEED_Y / 2.0 + 0.5
        else:
            myspeed = 1
        
        myspeed *= 1 + self.__level / 10.0
        return myspeed

class TurretMissile(Missile):
    speedRange = [7, 8]
    explosionClass = AllyExplosion
    COLOR = COLOR_BLUE

    def __init__(self, initPoint, targetPoint, nuke=False):
        self.__isNuke = nuke
        if nuke:
            self.speedRange = [3, 3]
            self.TRAIL_THICKNESS = 4
            self.explosionClass = NukeExplosion
        
        super(TurretMissile, self).__init__(initPoint, targetPoint)
        
    def collisionCheck(self, dt):
        v = self.speedVector(dt)
        if sqdist(self.traj.pos2, self.targetPoint) <= (v.x ** 2 + v.y ** 2):
            self.explode()
        

class Target(LayeredSprite):
    objects = []
    defaultLives = 3
    def __init__(self, slot, node):
        self.layer.appendChild(node)
        node.pos = slot
        self.isDead = False
        self.lives = self.defaultLives
        self.objects.append(self)
    
    def hit(self):
        self.lives -= 1
        if self.lives == 0:
            self.destroy()
            return True
        else:
            return False
    
    def destroy(self):
        self.isDead = True
        self._node.unlink()
        self.base.unlink()
        self.objects.remove(self)
    
    def getHitPos(self):
        return self._node.pos + Point2D(10, 10)
    
    def __repr__(self):
        return '%s %s' % (self.__class__.__name__, self._node.pos)
        
    @classmethod
    def filter(cls, subClass):
        return [t for t in cls.objects if isinstance(t, subClass)]


class Turret(Target):
    LIVES_COLORS = {3: '4444ff', 2: 'aa44cc', 1: 'ff4444', 0: 'ff1111'}
    def __init__(self, slot, ammo):
        self._node = avg.DivNode()
        self.base = avg.PolygonNode(pos=((10,0), (0, 20), (20, 20)), fillopacity=1,
                fillcolor=self.LIVES_COLORS[self.defaultLives], opacity=0,
                parent=self._node)
        self.__ammoGauge = Gauge(COLOR_BLUE, Gauge.LAYOUT_HORIZONTAL,
            pos=(0, 25), size=(20, 5), opacity=0.5, parent=self._node)
        
        self.nukeAlert = avg.ImageNode(href='nuke_alert.png', pos=(0, 35),
            opacity=0, parent=self._node)
        
        self.__ammo = ammo
        self.__initialAmmo = ammo
        self.__hasNuke = False
        self.__nukeAnim = None
        super(Turret, self).__init__(slot, self._node)
    
    def fire(self, pos):
        if self.__hasNuke:
            TurretMissile(self._node.pos + Point2D(10, 0), pos, nuke=True)
            self.__hasNuke = False
            EmpCommand().getState('game').nukeFired = True
        else:
            if self.__ammo > 0:
                self.__ammo -= 1
                self.__updateGauge()
                TurretMissile(self._node.pos + Point2D(10, 0), pos)
                return True
            else:
                return False
    
    def __updateGauge(self):
        self.__ammoGauge.setFVal(float(self.__ammo) / self.__initialAmmo)
        if self.__ammo == 5:
            self.__ammoGauge.setColor(COLOR_RED)
            TextFeedback(self._node.pos, 'Low ammo!', COLOR_RED)
        elif self.__ammo > 5:
            self.__ammoGauge.setColor(COLOR_BLUE)
        
    def getAmmo(self):
        return self.__ammo
        
    def hasAmmo(self):
        return self.__ammo > 0
        
    def hit(self):
        rc = super(Turret, self).hit()
        self.base.fillcolor = self.LIVES_COLORS[self.lives]
        return rc
    
    def destroy(self):
        if self.__nukeAnim:
            self.__nukeAnim.setStopCallback(None)
            self.__nukeAnim.abort()
            
        super(Turret, self).destroy()
            
    def rechargeAmmo(self):
        self.__ammo = self.__initialAmmo
        self.__updateGauge()
        EmpCommand().getState('game').updateAmmoGauge()
        
    def loadNuke(self):
        if not self.__hasNuke:
            self.__hasNuke = True
            self.__fadeInNukeAlert()
    
    def __fadeInNukeAlert(self):
        self.__nukeAnim = avg.fadeIn(self.nukeAlert, 100, 1, self.__fadeOutNukeAlert)
        
    def __fadeOutNukeAlert(self):
        if self.__hasNuke:
            cb = self.__fadeInNukeAlert
        else:
            cb = None
        
        self.__nukeAnim = avg.fadeOut(self.nukeAlert, 100, cb)
        
    def __repr__(self):
        return 'Turret: a=%d l=%d' %(self.__ammo, self.lives)
    
class City(Target):
    defaultLives = 1
    def __init__(self, slot):
        self._node = avg.DivNode()
        self.base = avg.PolygonNode(pos=((0,0), (10, 5), (20, 0), (20, 10), (0, 10)),
                fillopacity=1, fillcolor='8888ff', opacity=0, parent=self._node)
        super(City, self).__init__(slot, self._node)


class GameWordsNode(avg.WordsNode):
    def __init__(self, *args, **kwargs):
        kwargs['font'] = 'uni 05_53'
        kwargs['sensitive'] = False
        super(GameWordsNode, self).__init__(*args, **kwargs)


class Gauge(avg.DivNode):
    LAYOUT_VERTICAL='vertical'
    LAYOUT_HORIZONTAL='horizontal'
    
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

# STATES

class Game(engine.FadeGameState):
    GAMESTATE_INITIALIZING='INIT'
    GAMESTATE_PLAYING='PLAY'
    GAMESTATE_ULTRASPEED='ULTRA'
    def _init(self):
        avg.LineNode(pos1=(0, RESOLUTION.y - INVALID_TARGET_Y_OFFSET),
            pos2=(1280, RESOLUTION.y - INVALID_TARGET_Y_OFFSET), color='222222',
            strokewidth=0.8, parent=self)

        Target.initLayer(self)
        Missile.initLayer(self)
        Bonus.initLayer(self)
        TextFeedback.initLayer(self)
        Explosion.initLayer(self)
        TouchFeedback.initLayer(self)
        
        self.gameData = {}
        self.nukeFired = False
        self.__score = 0
        self.__enemiesToSpawn = 0
        self.__enemiesGone = 0
        self.__gameState = self.GAMESTATE_INITIALIZING
        self.__wave = 0
        
        self.__scoreText = GameWordsNode(text='0', pos=(640, 100), alignment='center',
            fontsize=50, opacity=0.5, parent=self)
        self.__teaser = GameWordsNode(text='', pos=(640, 300), alignment='center',
            fontsize=70, opacity=0.5, parent=self)
        
        self.__ammoGauge = Gauge(COLOR_BLUE, Gauge.LAYOUT_VERTICAL,
            pos=(20, RESOLUTION.y - INVALID_TARGET_Y_OFFSET - 350), size=(15, 300),
            opacity=0.3, parent=self)
        GameWordsNode(text='AMMO', pos=(17, RESOLUTION.y - INVALID_TARGET_Y_OFFSET - 45),
            fontsize=8, opacity=0.5, parent=self)
        
        self.__enemiesGauge = Gauge(COLOR_RED, Gauge.LAYOUT_VERTICAL,
            pos=(RESOLUTION.x - 35, RESOLUTION.y - INVALID_TARGET_Y_OFFSET - 350),
            size=(15, 300), opacity=0.3, parent=self)
        GameWordsNode(text='ENMY',
            pos=(RESOLUTION.x - 38, RESOLUTION.y - INVALID_TARGET_Y_OFFSET - 45), fontsize=8,
            opacity=0.5, parent=self)
        
        if DEBUG:
            self.__debugArea = GameWordsNode(pos=(10,10), size=(300, 600), fontsize=8,
                color='ffffff', opacity=0.7, parent=self)
        
    def _preTransIn(self):
        self.reset()
    
    def _postTransIn(self):
        self.nextWave()
    
    def _preTransOut(self):
        self.__changeGameState(self.GAMESTATE_INITIALIZING)
        
    def reset(self):
        self.__targets = []
        self.gameData = {
                'initialEnemies': 0,
                'initialAmmo': 0,
                'initialCities': 0,
                'enemiesDestroyed': 0,
                'ammoFired': 0,
            }
            
        for obj in Target.objects + Missile.objects:
            obj.destroy()
        
    def setNewGame(self):
        self.__wave = 0
        self.__score = 0
        
    def nextWave(self):
        Missile.speedMul = 1
        self.nukeFired = False
        self.__wave += 1
        self.__enemiesToSpawn = self.__wave * ENEMIES_WAVE_MULT
        self.__enemiesGone = 0
        self.gameData['initialEnemies'] = self.__enemiesToSpawn

        slots = [Point2D(x * SLOT_WIDTH, RESOLUTION.y - 60)
            for x in xrange(1, int(RESOLUTION.x / SLOT_WIDTH + 1))]
        random.shuffle(slots)
        
        for i in xrange(0, TURRETS_AMOUNT):
            Turret(slots.pop(), self.__wave * AMMO_WAVE_MULT)
        
        self.gameData['initialAmmo'] = self.__wave * AMMO_WAVE_MULT * TURRETS_AMOUNT
        self.gameData['initialCities'] = random.randrange(1, len(slots))
        for c in xrange(0, self.gameData['initialCities']):
            City(slots.pop())

        self.__ammoGauge.setColor(COLOR_BLUE)
        self.__ammoGauge.setFVal(1)
        self.__enemiesGauge.setFVal(1)

        self.playTeaser('Wave %d' % self.__wave)
        self.__changeGameState(self.GAMESTATE_PLAYING)
        g_Log.trace(g_Log.APP, 'Entering wave %d: %s' % (
                self.__wave, str(self.gameData))
            )
    
    def playTeaser(self, text):
        self.__teaser.text = text
        avg.fadeIn(self.__teaser, 200, 1, self.__teaserTimer)
    
    def getScore(self):
        return self.__score
        
    def setScore(self, val):
        if self.__score != val:
            update = True
        else:
            update = False
            
        self.__score = val
        
        if update:
            self.__scoreText.text = str(self.__score)
    
    def getLevel(self):
        return self.__wave
        
    def addScore(self, add):
        newscore = self.__score + int(add)
        if newscore < 0:
            newscore = 0
        self.setScore(newscore)
        
    def _update(self, dt):
        if self.__gameState != self.GAMESTATE_INITIALIZING:
            if DEBUG:
                ammoRatio = float(self.gameData['ammoFired']) / self.gameData['initialAmmo']
                self.__debugArea.text = (
                    ('dt=%03dms ets=%d ar=%1.2f' % (dt,
                        self.__enemiesToSpawn, ammoRatio)) + '<br/>' +
                    str(self.gameData) + '<br/>' +
                    str(Target.objects) + '<br/>' +
                    '<br/>'.join(map(str, Missile.filter(Enemy))) + '<br/>' +
                    '<br/>'.join(map(str, Missile.filter(TurretMissile)))
                    )

            Missile.update(dt)
            self.__checkGameStatus()
            self.__spawnEnemies()
    
    def _onTouch(self, event):
        turrets = filter(lambda o: o.hasAmmo(), Target.filter(Turret))
        if turrets:
            if event.pos.y < RESOLUTION.y - INVALID_TARGET_Y_OFFSET:
                if len(turrets) > 1:
                    d = abs(turrets[0].getHitPos().x - event.pos.x)
                    selectedTurret = turrets[0]
                
                    for t in turrets[1:]:
                        if abs(t.getHitPos().x - event.pos.x) < d:
                            d = abs(t.getHitPos().x - event.pos.x)
                            selectedTurret = t
                else:
                    selectedTurret = turrets[0]
                    
                selectedTurret.fire(event.pos)
                self.gameData['ammoFired'] += 1
                self.updateAmmoGauge()
                
                TouchFeedback(event.pos, COLOR_BLUE)
            else:
                TouchFeedback(event.pos, COLOR_RED)
        else:
            TouchFeedback(event.pos, COLOR_RED)
            TextFeedback(event.pos, 'Ammo depleted!', COLOR_RED)
    
    def _onKey(self, event):
        if DEBUG:
            if event.keystring == 'x':
                self.engine.changeState('gameover')
                return True
            elif event.keystring == 'r':
                self.engine.changeState('results')
                return True
            elif event.keystring == 'd':
                Target.filter(Turret)[0].hit()
                self.updateAmmoGauge()
                return True
            elif event.keystring == 'u':
                Missile.speedMul = ULTRASPEED_MISSILE_MUL
                self.__changeGameState(self.GAMESTATE_ULTRASPEED)
                return True
            elif event.keystring == 'n':
                self.__wave = 15
                self.engine.changeState('game')
                return True
            elif event.keystring == 'b':
                NukeBonus((200, 200))
                return True
            elif event.keystring == 'a':
                AmmoBonus((300, 200))
                return True
            elif event.keystring == 'k':
                map(lambda o: o.explode(), Missile.filter(Enemy))
                return True
    
    def updateAmmoGauge(self):
        ammo = 0
        for t in Target.filter(Turret):
            ammo += t.getAmmo()
        
        fdammo = self.gameData['initialAmmo'] - ammo
        afv = 1 - float(fdammo) / self.gameData['initialAmmo']
        if afv < 0.2:
            self.__ammoGauge.setColor(COLOR_RED)
        self.__ammoGauge.setFVal(afv)
        
    def enemyDestroyed(self, enemy, target=None):
        self.__enemiesGone += 1
        self.__enemiesGauge.setFVal(
                1 - float(self.__enemiesGone) /
                self.gameData['initialEnemies']
            )
        if target is None:
            self.addScore(ENEMY_DESTROYED_SCORE)
            self.gameData['enemiesDestroyed'] += 1
        else:
            if not target.isDead and target.hit():
                TextFeedback(target.getHitPos(), 'BUSTED!', COLOR_RED)
                # If we lose a turret, ammo stash sinks with it
                self.updateAmmoGauge()
        
    def __checkGameStatus(self):
        # Game end
        if not Target.filter(Turret):
            self.engine.changeState('gameover')
        
        # Wave end
        if not self.__enemiesToSpawn and not Missile.filter(Enemy):
            g_Log.trace(g_Log.APP, 'Wave ended')
            self.engine.changeState('results')
        
        # Switch to ultraspeed if there's nothing the player can do
        if (self.__gameState == self.GAMESTATE_PLAYING and
            self.__ammoGauge.getFVal() == 0 and
            not Missile.filter(TurretMissile) and
            not Explosion.filter(AllyExplosion)):
                Missile.speedMul = ULTRASPEED_MISSILE_MUL
                self.__changeGameState(self.GAMESTATE_ULTRASPEED)

    def __spawnEnemies(self):
        if (self.__enemiesToSpawn and Target.objects and
            (self.__gameState == self.GAMESTATE_ULTRASPEED or 
                random.randrange(0, 100) <= self.__wave)):
                    origin = Point2D(random.randrange(0, RESOLUTION.x), 0)
                    target = random.choice(Target.objects)
                    Enemy(origin, target, self.__wave)
                    self.__enemiesToSpawn -= 1
    
    def __teaserTimer(self):
        g_Player.setTimeout(1000, lambda: avg.fadeOut(self.__teaser, 3000))
    
    def __changeGameState(self, newState):
        g_Log.trace(g_Log.APP, 'Gamestate %s -> %s' % (self.__gameState, newState))
        self.__gameState = newState
        

class Results(engine.FadeGameState):
    def _init(self):
        self.__resultHeader = GameWordsNode(
            pos=(RESOLUTION.x / 2, RESOLUTION.y / 2 - 140), alignment='center',
            fontsize=70, color='ff2222', parent=self)
        
        self.__resultsParagraph = GameWordsNode(
            pos=(RESOLUTION.x / 2, RESOLUTION.y / 2 - 40), alignment='center',
            fontsize=40, color='aaaaaa', parent=self)
    
    def _preTransIn(self):
        self.__resultHeader.text = 'Wave %d results' % (
                self.engine.getState('game').getLevel()
            )
        self.__resultsParagraph.text = ''
    
    def _postTransIn(self):
        gameState = self.engine.getState('game')
        self.rows = [
            'Enemies destroyed: %d / %d' % (
                    gameState.gameData['enemiesDestroyed'],
                    gameState.gameData['initialEnemies'],
                ),
            'Cities saved: %d / %d' % (
                    len(Target.filter(City)), 
                    gameState.gameData['initialCities'],
                ),
            'Cities bonus: %d' % (len(Target.filter(City)) * CITY_RESCUE_SCORE),
        ]
        
        if self.engine.getState('game').nukeFired:
            self.rows.append('EMP Missiles launched: %d' % gameState.gameData['ammoFired'])
        else:
            self.rows.append(
                'EMP Missiles launched: %d (%d%% accuracy)' % (
                        gameState.gameData['ammoFired'],
                        self.__getAccuracy(),
                    ),
            )

        gameState.addScore(len(Target.filter(City)) * CITY_RESCUE_SCORE)
        g_Player.setTimeout(RESULTS_ADDROW_DELAY, self.addResultRow)
    
    def returnToGame(self):
        self.engine.changeState('game')
        
    def addResultRow(self):
        row = self.rows[0]
        self.rows.remove(row)
        self.__resultsParagraph.text += row + '<br/>'
        
        if self.rows:
            g_Player.setTimeout(RESULTS_ADDROW_DELAY, self.addResultRow)
        else:
            g_Player.setTimeout(RESULTS_DELAY, self.returnToGame)
    
    def __getAccuracy(self):
        mfired = self.engine.getState('game').gameData['ammoFired']
        if mfired == 0:
            return 0
        else:
            return (
                float(self.engine.getState('game').gameData['enemiesDestroyed']) /
                self.engine.getState('game').gameData['ammoFired'] * 100
                )
    
class GameOver(engine.FadeGameState):
    def _init(self):
        GameWordsNode(text='Game Over', pos=(RESOLUTION.x / 2, RESOLUTION.y / 2 - 80),
            alignment='center', fontsize=70, color='ff2222', parent=self)
        self.__score = GameWordsNode(pos=(RESOLUTION.x / 2, RESOLUTION.y / 2 + 20),
            alignment='center', fontsize=40, color='aaaaaa', parent=self)
        self.__timeout = None
    
    def _preTransIn(self):
        self.__score.text = 'Score: %d' % self.engine.getState('game').getScore()
        
    def _postTransIn(self):
        self.__timeout = g_Player.setTimeout(GAMEOVER_DELAY, self.__returnToMenu)
    
    def __returnToMenu(self):
        self.__timeout = None
        self.engine.changeState('menu')
    
class Menu(engine.FadeGameState):
    def _init(self):
        avg.ImageNode(href='logo.png', pos=(0, RESOLUTION.y - 562), parent=self)

        startText = GameWordsNode(text='Touch here to start', fontsize=30,
            opacity=0.5, parent=self)
        startText.pos = (RESOLUTION -
            startText.getMediaSize() - Point2D(50, RESOLUTION.y / 2))
        
        self.__startButton = avg.RectNode(pos=startText.pos - Point2D(10, 10),
            size=startText.getMediaSize() + Point2D(10, 20), opacity=0, parent=self)
        
        self.__startButton.setEventHandler(avg.CURSORDOWN, avg.MOUSE | avg.TOUCH,
            self.__onStartGame)

        if DEBUG:
            self.__startButton.fillopacity = 0.1

        if self.engine.exitButton:
            exitText = GameWordsNode(text='X', fontsize=60, color='444444', parent=self)
            exitText.pos = Point2D(RESOLUTION.x - exitText.getMediaSize().x - 30, 30)
            
            self.__exitButton = avg.RectNode(pos=exitText.pos - Point2D(20, 20),
                size=exitText.getMediaSize() + Point2D(20, 30), opacity=0, parent=self)
            
            if DEBUG:
                self.__exitButton.fillopacity = 0.1
        
            self.__exitButton.setEventHandler(avg.CURSORDOWN, avg.MOUSE | avg.TOUCH,
                self.__onLeaveApp)
    
    def _pause(self):
        self.__setButtonsActive(False)
    
    def _resume(self):
        self.__setButtonsActive(True)
        
    def _postTransIn(self):
        self.__setButtonsActive(True)

    def _onKey(self, event):
        if DEBUG:
            if event.keystring == 's':
                self.engine.changeState('game')
                return True

    def __setButtonsActive(self, active):
        self.__startButton.sensitive = active
        if self.engine.exitButton:
            self.__exitButton.sensitive = active
        
    def __onLeaveApp(self, e):
        self.__setButtonsActive(False)
        self.engine.leave()

    def __onStartGame(self, e):
        self.__setButtonsActive(False)
        self.engine.getState('game').setNewGame()
        self.engine.changeState('game')
    

class EmpCommand(engine.Engine):
    __metaclass__ = engine.Singleton
    
    multitouch = True
    exitButton = True
    def __init__(self, *args, **kwargs):
        avg.WordsNode.addFontDir(AVGAppUtil.getMediaDir(__file__, 'fonts'))
        super(EmpCommand, self).__init__(*args, **kwargs)

    def init(self):
        # If the program is called by an appchooser, change screen's resolution
        global RESOLUTION
        RESOLUTION = g_Player.getRootNode().size
        
        self._parentNode.mediadir = AVGAppUtil.getMediaDir(__file__)
        avg.RectNode(fillopacity=1, fillcolor='000000', opacity=0,
            size=RESOLUTION, parent=self._parentNode)

        self.registerState('menu', Menu())
        self.registerState('game', Game())
        self.registerState('gameover', GameOver())
        self.registerState('results', Results())
        
        self.bootstrap('menu')

if __name__ == '__main__':
    EmpCommand.exitButton = False
    if DEBUG:
        import cProfile
        cProfile.run('EmpCommand.start(resolution=RESOLUTION)')
    else:
        EmpCommand.start(resolution=RESOLUTION)

