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
TURRETS_AMOUNT = 3

RESOLUTION = Point2D(1280, 720)

INVALID_TARGET_Y = RESOLUTION.y - 100

DEBUG = False

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
        self.__anim = avg.ParallelAnim((diman, opaan), None, self.__cleanup)
        self.__anim.start()
        self.objects.append(self)
    
    def __cleanup(self):
        self.__anim.abort()
        del self.__anim
        self._node.unlink()
        self.objects.remove(self)
    
class AllyExplosion(Explosion):
    DURATION = 500
    RADIUS = 60
    COLOR = COLOR_BLUE
    
    def __init__(self, pos):
        self.hits = 0
        super(AllyExplosion, self).__init__(pos)

    def addHit(self):
        self.hits += 1

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
        
# Abstract
class Missile(LayeredSprite):
    objects = []
    def __init__(self, initPoint, targetPoint, explCallback=None):
        self.initPoint = initPoint
        self.targetPoint = targetPoint
        self.explCallback = explCallback
        self.__isExploding = False
            
        self.traj = avg.LineNode(pos1=self.initPoint, pos2=self.initPoint,
            color=self.COLOR, parent=self.layer)

        self.speed = random.uniform(*self.speedRange)
        self.__fade = None
        self.objects.append(self)
    
    def explode(self):
        if not self.__isExploding:
            self.__isExploding = True
            self.__fade = avg.fadeOut(
                self.traj, self.explosionClass.DURATION / 2, self.__cleanup)
            self.explosionClass(self.traj.pos2)
        
            if self.explCallback:
                self.explCallback(self,
                    sqdist(self.traj.pos2, self.targetPoint) <= self.speed ** 2)
    
    def destroy(self):
        if self.__fade:
            self.__fade.abort()
        
        self.__cleanup()

    def checkIntercept(self):
        pass
    
    def getSpeedFactor(self):
        return 1
        
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
    def update(cls):
        for m in cls.objects:
            if not m.__isExploding:
                m.traj.pos2 += (
                    (m.targetPoint - m.initPoint).getNormalized() *
                        m.speed *
                        m.getSpeedFactor()
                        )
                m.checkIntercept()
                if sqdist(m.traj.pos2, m.targetPoint) <= m.speed ** 2:
                    m.explode()

class Enemy(Missile):
    speedRange = [0.5, 1]
    explosionClass = EnemyExplosion
    COLOR = COLOR_RED
    
    def __init__(self, initPoint, targetPoint, level, explCallback=None):
        self.__level = level
        super(Enemy, self).__init__(initPoint, targetPoint, explCallback)
        
    def checkIntercept(self):
        for exp in Explosion.objects:
            if (isinstance(exp, AllyExplosion) and
                sqdist(exp._node.pos, self.traj.pos2) < exp._node.r ** 2):
                    exp.addHit()
                    if exp.hits == GREAT_HITS:
                        TextFeedback(exp._node.pos, 'GREAT!', COLOR_BLUE)
                    self.explode()

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


class Target(LayeredSprite):
    objects = []
    defaultLives = 3
    def __init__(self, slot, node):
        self.layer.appendChild(node)
        node.pos = slot
        self.lives = self.defaultLives
        self.objects.append(self)
    
    def hit(self):
        self.lives -= 1
        if self.lives == 0:
            self.destroy()
    
    def destroy(self):
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
        self.__ammo = ammo
        self.__initialAmmo = ammo
        super(Turret, self).__init__(slot, self._node)
    
    def fire(self, pos):
        self.__ammo -= 1
        self.__ammoGauge.setFVal(float(self.__ammo) / self.__initialAmmo)
        if self.__ammo > 0:
            if self.__ammo == 5:
                self.__ammoGauge.setColor(COLOR_RED)
                TextFeedback(self._node.pos, 'Low ammo!', COLOR_RED)
            TurretMissile(self._node.pos + Point2D(10, 0), pos)
            return True
        else:
            return False
    
    def hasAmmo(self):
        return self.__ammo > 0
        
    def hit(self):
        super(Turret, self).hit()
        self.base.fillcolor = self.LIVES_COLORS[self.lives]
    
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
    
    def setColor(self, color):
        self.__level.fillcolor = color

# STATES

class Game(engine.FadeGameState):    
    def _init(self):
        avg.LineNode(pos1=(0, INVALID_TARGET_Y), pos2=(1280, INVALID_TARGET_Y),
            color='222222', strokewidth=0.8, parent=self)

        Target.initLayer(self)
        Missile.initLayer(self)
        TextFeedback.initLayer(self)
        Explosion.initLayer(self)
        TouchFeedback.initLayer(self)
        
        self.gameData = {}
        self.__score = 0
        self.__enemiesToSpawn = 0
        self.__isPlaying = False
        self.__wave = 0
        
        self.__scoreText = GameWordsNode(text='0', pos=(640, 100), alignment='center',
            fontsize=50, opacity=0.5, parent=self)
        self.__teaser = GameWordsNode(text='', pos=(640, 300), alignment='center',
            fontsize=70, opacity=0.5, parent=self)
        
        self.__ammoGauge = Gauge(COLOR_BLUE, Gauge.LAYOUT_VERTICAL,
            pos=(20, INVALID_TARGET_Y - 350), size=(15, 300), opacity=0.3, parent=self)
        
        self.__enemiesGauge = Gauge(COLOR_RED, Gauge.LAYOUT_VERTICAL,
            pos=(RESOLUTION.x - 35, INVALID_TARGET_Y - 350), size=(15, 300),
            opacity=0.3, parent=self)
        
        if DEBUG:
            self.__debugArea = GameWordsNode(pos=(10,10), size=(300, 600), fontsize=8,
                color='ffffff', opacity=0.7, parent=self)
        
    def _preTransIn(self):
        self.reset()
    
    def _postTransIn(self):
        self.nextWave()
    
    def _preTransOut(self):
        self.__isPlaying = False
        
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
        self.__wave += 1
        self.__enemiesToSpawn = self.__wave * ENEMIES_WAVE_MULT
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
        self.__isPlaying = True
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
        
    def _update(self):
        Missile.update()
        
        if DEBUG:
            self.__debugArea.text = (str(Target.objects) + '<br/>' +
                '<br/>'.join(map(str, Missile.filter(Enemy))) + '<br/>' +
                '<br/>'.join(map(str, Missile.filter(TurretMissile)))
                )
            
        if self.__isPlaying:
            if (self.__enemiesToSpawn and
                random.randrange(0, 100) <= self.__wave and # magic spawner
                Target.objects):
                    origin = Point2D(random.randrange(0, RESOLUTION.x), 0)
                    tpoint = random.choice(Target.objects).getHitPos()
                    Enemy(origin, tpoint, self.__wave, self.__enemyDestroyed)
                    self.__enemiesToSpawn -= 1

            self.__checkGameStatus()
    
    def _onTouch(self, event):
        turrets = filter(lambda o: o.hasAmmo(), Target.filter(Turret))
        if turrets:
            if event.pos.y < INVALID_TARGET_Y:
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
                
                afv = 1 - float(self.gameData['ammoFired']) / self.gameData['initialAmmo']
                if afv < 0.2:
                    self.__ammoGauge.setColor(COLOR_RED)
                self.__ammoGauge.setFVal(afv)
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
            if event.keystring == 'r':
                self.engine.changeState('results')
                return True
            
    def __enemyDestroyed(self, enemy, gotDestination):
        if not gotDestination:
            self.addScore(50)
            self.gameData['enemiesDestroyed'] += 1
            self.__enemiesGauge.setFVal(
                    1 - float(self.gameData['enemiesDestroyed']) /
                    self.gameData['initialEnemies']
                )
        else:
            for obj in Target.objects:
                if sqdist(obj.getHitPos(), enemy.traj.pos2) <= enemy.speed ** 2:
                    obj.hit()
                    TextFeedback(obj.getHitPos(), 'BUSTED!', COLOR_RED)
                    return
        
    def __checkGameStatus(self):
        if not Target.filter(Turret):
            self.engine.changeState('gameover')
    
        if not self.__enemiesToSpawn and not Missile.filter(Enemy):
            g_Log.trace(g_Log.APP, 'Wave ended')
            self.engine.changeState('results')
            
    def __teaserTimer(self):
        g_Player.setTimeout(1000, lambda: avg.fadeOut(self.__teaser, 3000))
    

class Results(engine.FadeGameState):
    def _init(self):
        self.__resultHeader = GameWordsNode(
            pos=(RESOLUTION.x / 2, RESOLUTION.y / 2 - 140), alignment='center',
            fontsize=70, opacity=0.5, color='ff2222', parent=self)
        
        self.__resultsParagraph = GameWordsNode(
            pos=(RESOLUTION.x / 2, RESOLUTION.y / 2 - 40), alignment='center',
            fontsize=40, opacity=0.5, color='aaaaaa', parent=self)
    
    def _preTransIn(self):
        self.__resultHeader.text = 'Wave %d results' % (
                self.engine.proxyState('game').getLevel()
            )
        self.__resultsParagraph.text = ''
    
    def _postTransIn(self):
        gameState = self.engine.proxyState('game')
        self.rows = [
            'Enemies destroyed: %d / %d' % (
                    gameState.gameData['enemiesDestroyed'],
                    gameState.gameData['initialEnemies'],
                ),
            'Cities saved: %d / %d' % (
                    len(Target.filter(City)), 
                    gameState.gameData['initialCities'],
                ),
            'Cities bonus: %d' % (len(Target.filter(City))*800),
            'EMP Missiles launched: %d (%d%% accuracy)' % (
                    gameState.gameData['ammoFired'],
                    self.__getAccuracy(),
                ),
        ]
        gameState.addScore(len(Target.filter(City))*800)
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
        mfired = self.engine.proxyState('game').gameData['ammoFired']
        if mfired == 0:
            return 0
        else:
            return (
                float(self.engine.proxyState('game').gameData['enemiesDestroyed']) /
                self.engine.proxyState('game').gameData['ammoFired'] * 100
                )
    
class GameOver(engine.FadeGameState):
    def _init(self):
        GameWordsNode(text='Game Over', pos=(RESOLUTION.x / 2, RESOLUTION.y / 2 - 80),
            alignment='center', fontsize=70, opacity=1, color='ff2222', parent=self)
        self.__score = GameWordsNode(pos=(RESOLUTION.x / 2, RESOLUTION.y / 2 + 20),
            alignment='center', fontsize=40, color='aaaaaa', opacity=0.5, parent=self)
        self.__timeout = None
    
    def _preTransIn(self):
        self.__score.text = 'Score: %d' % self.engine.proxyState('game').getScore()
        
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
        if self.engine.exitButton:
            self.__exitButton.sensitive = False

        self.__startButton.sensitive = False
        self.engine.proxyState('game').setNewGame()
        self.engine.changeState('game')
    

class EmpCommand(engine.Engine):
    multitouch = True
    exitButton = True
    def __init__(self, *args, **kwargs):
        avg.WordsNode.addFontDir(AVGAppUtil.getMediaDir(__file__, 'fonts'))
        super(EmpCommand, self).__init__(*args, **kwargs)

    def init(self):
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
    EmpCommand.start(resolution=RESOLUTION)

