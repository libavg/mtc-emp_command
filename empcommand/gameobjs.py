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


import random
import math

from libavg import avg, Point2D, player
from empcommand import app

import engine
import widgets
import consts


__all__ = ['Explosion', 'Target', 'Missile', 'TextFeedback', 'TouchFeedback', 'Bonus',
        'Turret', 'City', 'Enemy', 'TurretMissile', 'AmmoBonus', 'NukeBonus',
        'EmpExplosion', 'EnemyExplosion']

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
    cb = None

    def __init__(self, pos):
        self._node = avg.CircleNode(pos=pos, r=app().rnorm(20), fillcolor=self.COLOR,
                opacity=0, fillopacity=1, parent=self.layer)

        targetRadius = app().rnorm(self.RADIUS)
        if app().difficultyLevel == 2:
            targetRadius *= 0.8

        diman = avg.EaseInOutAnim(self._node, 'r', self.DURATION, 1,
                targetRadius, self.DURATION / 3, self.DURATION * 2 / 3)
        opaan = avg.EaseInOutAnim(self._node, 'fillopacity', self.DURATION, 1, 0,
                self.DURATION, 0)
        self.__anim = avg.ParallelAnim((diman, opaan), None, self._cleanup)
        self.__anim.start()

        if self.SOUND:
            engine.SoundManager.play(random.choice(self.SOUND), randomVolume=True)

        self.objects.append(self)
        
        if self.cb is not None:
            self.cb()

    def _cleanup(self):
        self.__anim.abort()
        del self.__anim
        self._node.unlink(True)
        self.objects.remove(self)

    @classmethod
    def filter(cls, subClass):
        return [t for t in cls.objects if isinstance(t, subClass)]
    
    @classmethod
    def registerCallback(cls, cb):
        cls.cb = cb


class EmpExplosion(Explosion):
    DURATION = 500
    RADIUS = 60
    COLOR = consts.COLOR_BLUE
    SOUND = ['emp.ogg']

    def __init__(self, pos):
        self.hits = 0
        super(EmpExplosion, self).__init__(pos)

    def addHit(self):
        self.hits += 1

    def _cleanup(self):
        if self.hits == consts.GREAT_HITS:
            AmmoBonus(self._node.pos, 10000)
        elif self.hits == consts.NUKE_HITS:
            NukeBonus(self._node.pos, 20000)

        super(EmpExplosion, self)._cleanup()


class NukeExplosion(EmpExplosion):
    DURATION = 2500
    RADIUS = 600
    SOUND = ['nuke.ogg']

    def addHit(self):
        pass


class EnemyExplosion(Explosion):
    DURATION = 1000
    RADIUS = 40
    COLOR = consts.COLOR_RED
    SOUND = ['enemy_exp1.ogg', 'enemy_exp2.ogg', 'enemy_exp3.ogg',
            'enemy_exp4.ogg', 'enemy_exp5.ogg']


class TouchFeedback(LayeredSprite):
    def __init__(self, pos, color):
        self.__node = avg.CircleNode(color=color, strokewidth=2,
                parent=self.layer, r=app().rnorm(10), pos=pos)

        diman = avg.LinearAnim(self.__node, 'r', 200, app().rnorm(10), app().rnorm(20))
        opaan = avg.LinearAnim(self.__node, 'opacity', 200, 1, 0)
        self.__anim = avg.ParallelAnim((diman, opaan), None, self.__cleanup)
        self.__anim.start()

    def __cleanup(self):
        del self.__anim
        self.__node.unlink(True)


class TextFeedback(LayeredSprite):
    TRANSITION_TIME = 500
    def __init__(self, pos, text, color):
        self.__node = widgets.GameWordsNode(text=text, parent=self.layer,
                pos=pos, fontsize=30, color=color, alignment='center')

        diman = avg.LinearAnim(self.__node, 'fontsize', self.TRANSITION_TIME,
                app().ynorm(30), app().ynorm(60))
        opaan = avg.LinearAnim(self.__node, 'opacity', self.TRANSITION_TIME, 1, 0)
        offsan = avg.LinearAnim(self.__node, 'pos',
                self.TRANSITION_TIME, pos, pos - app().pnorm(Point2D(70, 70)))
        self.__anim = avg.ParallelAnim((diman, opaan, offsan), None, self.__cleanup)
        self.__anim.start()

    def __cleanup(self):
        del self.__anim
        self.__node.unlink(True)


class Bonus(LayeredSprite):
    TRANSITION_TIME = 200
    OPACITY = 0.8
    TRANSITION_ZOOM = 18
    DROP_RADIUS_SQ = 900

    spawnTimestamp = {}
    
    STATE_BUSY = 'STATE_BUSY'
    STATE_READY = 'STATE_READY'
    STATE_DRAGGING = 'STATE_DRAGGING'

    def __init__(self, pos, icon, waitTime):
        if (self.__class__ in self.spawnTimestamp and
                player.getFrameTime() - self.spawnTimestamp[self.__class__] < waitTime):
            return
        else:
            self.spawnTimestamp[self.__class__] = player.getFrameTime()

        self._state = self.STATE_BUSY
        self._tmr = player.setInterval(100, self.__tick)
        self._remainingTicks = consts.BONUS_AVAILABILITY_TICKS
        
        self._node = widgets.RIImage(href=icon, pos=pos, parent=self.layer)
        diman = avg.LinearAnim(self._node, 'size', self.TRANSITION_TIME,
                self._node.getMediaSize() * self.TRANSITION_ZOOM,
                self._node.getMediaSize())
        opaan = avg.LinearAnim(self._node, 'opacity',
                self.TRANSITION_TIME, 0, self.OPACITY)
        offsan = avg.LinearAnim(self._node, 'pos', self.TRANSITION_TIME,
                Point2D(pos) - self._node.getMediaSize() * self.TRANSITION_ZOOM / 2, pos)
        self._anim = avg.ParallelAnim((diman, opaan, offsan), None, self.__ready)
        self._anim.start()
        self.__cursorid = None

        engine.SoundManager.play('bonus_alert.ogg')

    def _trigger(self):
        return False

    def _suckIn(self, pos, callback):
        self._state = self.STATE_BUSY
        diman = avg.LinearAnim(self._node, 'size', self.TRANSITION_TIME,
                self._node.size, Point2D(1, 1))
        opaan = avg.LinearAnim(self._node, 'opacity', self.TRANSITION_TIME,
                self.OPACITY, 0)
        offsan = avg.LinearAnim(self._node, 'pos', self.TRANSITION_TIME,
                self._node.pos, pos)
        self._anim = avg.ParallelAnim((diman, opaan, offsan), None, callback)
        self._anim.start()

    def __move(self, event):
        if self.__cursorid == event.cursorid:
            self._node.pos = event.pos - self.__handlePos

    def __release(self, event):
        if self.__cursorid == event.cursorid:
            self._node.setEventHandler(avg.CURSORMOTION, avg.MOUSE | avg.TOUCH, None)
            self._node.setEventHandler(avg.CURSORUP, avg.MOUSE | avg.TOUCH, None)
            self._node.releaseEventCapture(self.__cursorid)
            self.__cursorid = None

            if not self._trigger():
                self._state = self.STATE_READY
            else:
                engine.SoundManager.play('bonus_drop.ogg')

    def __startDrag(self, event):
        if self.__cursorid is None:
            self._node.setEventCapture(event.cursorid)
            self._state = self.STATE_DRAGGING
            self._node.setEventHandler(avg.CURSORUP, avg.MOUSE | avg.TOUCH,
                    self.__release)
            self._node.setEventHandler(avg.CURSORMOTION, avg.MOUSE | avg.TOUCH,
                    self.__move)
            self.__cursorid = event.cursorid
            self.__handlePos = event.pos - self._node.pos

            self._node.opacity = self.OPACITY

            return True

    def __ready(self):
        self._node.setEventHandler(avg.CURSORDOWN,
                avg.MOUSE | avg.TOUCH, self.__startDrag)

        self._state = self.STATE_READY

    def __tick(self):
        if self._state == self.STATE_READY:
            self._remainingTicks -= 1
            if self._remainingTicks < 20:
                self.__blink()
            if self._remainingTicks == 0:
                self._state = self.STATE_BUSY
                self._destroy()
        
    def __blink(self):
        if self._node.opacity == 0:
            self._node.opacity = self.OPACITY
        else:
            self._node.opacity = 0
    
    def _destroy(self):
        self._state = self.STATE_BUSY
        player.clearInterval(self._tmr)
        if self._anim:
            self._anim.abort()
            del self._anim
            self._anim = None
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
        self.__lastSpeedVector = Point2D(0, 0)

        self.traj = avg.LineNode(pos1=self.initPoint, pos2=self.initPoint,
                color=self.COLOR, strokewidth=self.TRAIL_THICKNESS, parent=self.layer)

        self.nominalSpeedVec = ((self.targetPoint - self.initPoint).getNormalized() *
                app().rnorm(random.uniform(*self.speedRange)) / consts.DELTAT_NORM_FACTOR)
        self.__fade = None
        self.objects.append(self)

    def explode(self, pos):
        if not self.__isExploding:
            self.__isExploding = True
            self.__fade = avg.fadeOut(
                    self.traj, self.explosionClass.DURATION / 2, self.__cleanup)
            self.explosionClass(pos)

    def destroy(self):
        if self.__fade:
            self.__fade.setStopCallback(None)
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
        self.traj.unlink(True)
        self.objects.remove(self)

    def __repr__(self):
        return '%s %s -> (%d, %d) v=%.2f' % (self.__class__.__name__,
                self.initPoint,
                int(self.traj.pos2.x), int(self.traj.pos2.y),
                math.sqrt(self.__lastSpeedVector.x ** 2 + self.__lastSpeedVector.y ** 2),
                )

    @classmethod
    def filter(cls, subClass):
        return [t for t in cls.objects if isinstance(t, subClass)]

    @classmethod
    def update(cls, dt):
        for m in cls.objects:
            if not m.__isExploding:
                m.__lastSpeedVector = m.speedVector(dt)
                m.traj.pos2 += m.__lastSpeedVector
                m.collisionCheck(dt)


class Enemy(Missile):
    speedRange = [0.3, 0.7]
    explosionClass = EnemyExplosion
    COLOR = consts.COLOR_RED

    def __init__(self, initPoint, targetObj, level):
        self.__level = level
        # TODO: dangling reference
        self.__targetObj = targetObj
        super(Enemy, self).__init__(initPoint, targetObj.getHitPos())

    def collisionCheck(self, dt):
        # Check if the enemy enters an EMP shockwave
        for exp in Explosion.filter(EmpExplosion):
            if sqdist(exp._node.pos, self.traj.pos2) < exp._node.r ** 2:
                    exp.addHit()
                    if exp.hits == consts.GREAT_HITS:
                        TextFeedback(exp._node.pos, 'GREAT!', consts.COLOR_BLUE)
                    elif exp.hits == consts.NUKE_HITS:
                        TextFeedback(exp._node.pos, '** AWESOME **', consts.COLOR_BLUE)
                    self.explode(self.traj.pos2)
                    app().getState('game').enemyDestroyed(self)

        # Check if the enemy reached its destination
        v = self.speedVector(dt)
        if sqdist(self.traj.pos2, self.targetPoint) <= (v.x ** 2 + v.y ** 2):
            self.explode(self.targetPoint)
            app().getState('game').enemyDestroyed(self, self.__targetObj)

    def getSpeedFactor(self):
        return 1 + self.__level * consts.WAVE_ENEMY_SPEED_INCREASE_FACTOR


class TurretMissile(Missile):
    speedRange = [7, 8]
    explosionClass = EmpExplosion
    COLOR = consts.COLOR_BLUE

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
            self.explode(self.targetPoint)


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
            engine.SoundManager.play('target_destroy.ogg', randomVolume=True)
            return True
        else:
            engine.SoundManager.play('target_hit.ogg', randomVolume=True)
            return False

    def destroy(self):
        self.isDead = True
        self._node.unlink(True)
        self.base.unlink(True)
        self.objects.remove(self)

    def getHitPos(self):
        return self._node.pos + app().pnorm(Point2D(10, 10), diagNorm=True)

    def __repr__(self):
        return '%s %s' % (self.__class__.__name__, self._node.pos)

    @classmethod
    def filter(cls, subClass):
        return [t for t in cls.objects if isinstance(t, subClass)]


class Turret(Target):
    LIVES_COLORS = {3: '4444ff', 2: 'aa44cc', 1: 'ff4444', 0: 'ff1111'}
    def __init__(self, slot, ammo):
        self._node = avg.DivNode()
        self.base = avg.PolygonNode(
                pos=app().spnorm(((10, 0), (0, 20), (20, 20)), diagNorm=True),
                fillopacity=1, fillcolor=self.LIVES_COLORS[self.defaultLives],
                opacity=0, parent=self._node)
        self.__ammoGauge = widgets.Gauge(consts.COLOR_BLUE,
                widgets.Gauge.LAYOUT_HORIZONTAL,
                pos=app().pnorm((0, 25), diagNorm=True),
                size=app().pnorm((20, 5), diagNorm=True),
                opacity=0.5, parent=self._node)

        self.nukeAlert = widgets.RIImage(href='nuke_alert.png',
                pos=app().pnorm((0, 35), diagNorm=True),
                opacity=0, parent=self._node)

        self.__ammo = int(ammo)
        self.__initialAmmo = self.__ammo
        self.__hasNuke = False
        self.__nukeAnim = None
        super(Turret, self).__init__(slot, self._node)

    def fire(self, pos):
        if self.__hasNuke:
            TurretMissile(self._node.pos + app().pnorm((10, 0), diagNorm=True),
                    pos, nuke=True)
            self.__hasNuke = False
            app().getState('game').nukeFired = True
            engine.SoundManager.play('nuke_launch.ogg')
        else:
            if self.__ammo > 0:
                self.__ammo -= 1
                self.__updateGauge()
                TurretMissile(self._node.pos + app().pnorm((10, 0), diagNorm=True), pos)
                engine.SoundManager.play('missile_launch.ogg', randomVolume=True)
                return True
            else:
                return False

    def __updateGauge(self):
        self.__ammoGauge.setFVal(float(self.__ammo) / self.__initialAmmo)
        if self.__ammo == 5:
            self.__ammoGauge.setColor(consts.COLOR_RED)
        elif self.__ammo > 5:
            self.__ammoGauge.setColor(consts.COLOR_BLUE)

    def getAmmo(self):
        return self.__ammo

    def hasAmmo(self):
        return self.__ammo > 0 or self.__hasNuke

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
        app().getState('game').updateAmmoGauge()

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
        return 'Turret: a=%d l=%d' % (self.__ammo, self.lives)


class City(Target):
    defaultLives = 1
    def __init__(self, slot):
        self._node = avg.DivNode()
        self.base = avg.PolygonNode(
                pos=app().spnorm(((0, 0), (10, 5), (20, 0), (20, 10), (0, 10)),
                    diagNorm=True),
                fillopacity=1, fillcolor='8888ff', opacity=0, parent=self._node)
        super(City, self).__init__(slot, self._node)

