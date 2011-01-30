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
import random

from libavg import avg, Point2D, AVGAppUtil

from gameapp import app
import engine
import consts
import widgets
from gameobjs import *

g_Player = avg.Player.get()
g_Log = avg.Logger.get()


class Start(engine.FadeGameState):
    def _init(self):
        im = avg.ImageNode(href='logo.png', mipmap=True, parent=self)
        xfactor = app().size.x / im.getMediaSize().x / 2
        im.size = im.getMediaSize() * xfactor
        im.pos = (0, app().size.y - im.size.y)

        rightPane = avg.DivNode(pos=(app().xnorm(765), app().ynorm(90)), parent=self)
        
        self.__menu = widgets.Menu(onPlay=self.__onPlay, onAbout=self.__onAbout,
                onDiffChanged=self.__onDiffChanged, onQuit=self.__onQuit,
                width=app().xnorm(350), parent=rightPane)

        self.__hiscoreTab = widgets.HiscoreTab(db=app().scoreDatabase,
                pos=(0, app().ynorm(350)), size=(app().xnorm(350), app().ynorm(270)),
                parent=rightPane)
        
        self.registerBgTrack('theme.ogg')
        
        # widgets.GameWordsNode(text='PRERELEASE TEST - DO NOT DISTRIBUTE', fontsize=24,
        #         color='553333', pos=(20, 20), parent=self)

    def _resume(self):
        self.__hiscoreTab.refresh()
    
    def _preTransIn(self):
        self.__hiscoreTab.refresh()

    def _onKeyDown(self, event):
        self.__menu.onKeyDown(event)
        
        if consts.DEBUG:
            if event.keystring == 's':
                self.engine.changeState('game')
                return True

    def _update(self, dt):
        self.__hiscoreTab.update(dt)
        self.__menu.update(dt)

    def __onPlay(self):
        self.engine.getState('game').setNewGame()
        self.engine.changeState('game')

    def __onAbout(self):
        self.engine.changeState('about')
    
    def __onDiffChanged(self, ndiff):
        # TODO: implement difficulty level
        pass
        
    def __onQuit(self):
        app().quit()


class About(engine.FadeGameState):
    pass
    

class Game(engine.FadeGameState):
    GAMESTATE_INITIALIZING = 'INIT'
    GAMESTATE_PLAYING = 'PLAY'
    GAMESTATE_ULTRASPEED = 'ULTRA'

    def _init(self):
        # Sky
        avg.ImageNode(href='enmy_sky.png', size=(app().size.x, app().ynorm(300)),
                opacity=0.2, parent=self)
        self.clouds = widgets.Clouds(maxOpacity=0.3, size=(app().size.x,
                app().ynorm(600)), parent=self)
        EnemyExplosion.registerCallback(self.clouds.blink)
        
        # Allied ground
        a = app().xnorm(5)
        b = app().ynorm(10)
        c = app().xnorm(30)
        d = app().ynorm(5)
        avg.PolygonNode(
                pos=(
                    (-a, app().size.y - consts.INVALID_TARGET_Y_OFFSET + b),
                    (c, app().size.y - consts.INVALID_TARGET_Y_OFFSET),
                    (app().size.x - c, app().size.y - consts.INVALID_TARGET_Y_OFFSET),
                    (app().size.x + a, app().size.y - consts.INVALID_TARGET_Y_OFFSET + b),
                    (app().size.x + a, app().size.y + d),
                    (-a, app().size.y + d),
                ),
                color=consts.COLOR_BLUE,
                fillcolor=consts.COLOR_BLUE,
                opacity=0.3,
                fillopacity=0.05,
                parent=self
                )

        divPlayground = avg.DivNode(parent=self)
        divTouchables = avg.DivNode(parent=self)

        Target.initLayer(divPlayground)
        Missile.initLayer(divPlayground)
        TextFeedback.initLayer(divPlayground)
        Explosion.initLayer(divPlayground)
        TouchFeedback.initLayer(divPlayground)
        Bonus.initLayer(divTouchables)

        self.gameData = {}
        self.nukeFired = False
        self.__score = 0
        self.__enemiesToSpawn = 0
        self.__enemiesGone = 0
        self.__gameState = self.GAMESTATE_INITIALIZING
        self.__wave = 0

        engine.SoundManager.allocate('buzz.ogg')

        self.__scoreText = widgets.GameWordsNode(text='0',
                pos=(app().size.x / 2, app().ynorm(100)),
                alignment='center', fontsize=50, opacity=0.5, parent=self)
        self.__teaser = widgets.GameWordsNode(text='',
                pos=(app().size.x / 2, app().ynorm(300)),
                alignment='center', fontsize=70, opacity=0.5, parent=self)

        self.__ammoGauge = widgets.Gauge(consts.COLOR_BLUE,
                widgets.Gauge.LAYOUT_VERTICAL,
                pos=(app().xnorm(20),
                    app().size.y - consts.INVALID_TARGET_Y_OFFSET - app().ynorm(350)),
                size=(app().xnorm(15), app().ynorm(300)), parent=self)
        self.__ammoGauge.addLabel('AMMO')
        self.__ammoGauge.setOpacity(0.3)

        self.__enemiesGauge = widgets.Gauge(consts.COLOR_RED,
                widgets.Gauge.LAYOUT_VERTICAL,
                pos=(app().size.x - app().xnorm(35), app().size.y - \
                    consts.INVALID_TARGET_Y_OFFSET - app().ynorm(350)),
                size=(app().xnorm(15), app().ynorm(300)), parent=self)
        self.__enemiesGauge.addLabel('ENMY')
        self.__enemiesGauge.setOpacity(0.3)

        self.registerBgTrack('game_loop.ogg', maxVolume=0.3)

        if consts.DEBUG:
            self.__debugArea = widgets.GameWordsNode(pos=(10, 10), size=(300, 600),
                fontsize=8, color='ffffff', opacity=0.7, parent=self)

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
        self.setScore(0)

    def nextWave(self):
        Missile.speedMul = 1
        self.nukeFired = False
        self.__wave += 1
        self.__enemiesToSpawn = self.__wave * consts.ENEMIES_WAVE_MULT
        self.__enemiesGone = 0
        self.gameData['initialEnemies'] = self.__enemiesToSpawn

        slots = [Point2D(x * consts.SLOT_WIDTH, app().size.y - 60)
                for x in xrange(1, int(app().size.x / consts.SLOT_WIDTH + 1))]

        random.shuffle(slots)

        for i in xrange(0, consts.TURRETS_AMOUNT):
            Turret(slots.pop(), self.__wave * consts.AMMO_WAVE_MULT)

        self.gameData['initialAmmo'] = self.__wave * consts.AMMO_WAVE_MULT * \
                consts.TURRETS_AMOUNT
        self.gameData['initialCities'] = consts.CITIES

        for c in xrange(0, self.gameData['initialCities']):
            City(slots.pop())

        self.__ammoGauge.setColor(consts.COLOR_BLUE)
        self.__ammoGauge.setFVal(1)
        self.__enemiesGauge.setFVal(1)

        self.playTeaser('Wave %d' % self.__wave)
        self.__changeGameState(self.GAMESTATE_PLAYING)
        g_Log.trace(g_Log.APP, 'Entering wave %d: %s' % (
                self.__wave, str(self.gameData)))

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
            if consts.DEBUG:
                ammoRatio = float(
                        self.gameData['ammoFired']) / self.gameData['initialAmmo']
                self.__debugArea.text = (
                        ('dt=%03dms ets=%d ar=%1.2f' % (dt,
                            self.__enemiesToSpawn, ammoRatio)) + '<br/>' +
                        str(self.gameData) + '<br/>' +
                        str(Target.objects) + '<br/>' +
                        '<br/>'.join(map(str, Missile.filter(Enemy))) + '<br/>' +
                        '<br/>'.join(map(str, Missile.filter(TurretMissile))))

            Missile.update(dt)
            self.__checkGameStatus()
            self.__spawnEnemies()

    def _onTouch(self, event):
        turrets = filter(lambda o: o.hasAmmo(), Target.filter(Turret))
        if turrets:
            if event.pos.y < app().size.y - consts.INVALID_TARGET_Y_OFFSET:
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

                TouchFeedback(event.pos, consts.COLOR_BLUE)
            else:
                TouchFeedback(event.pos, consts.COLOR_RED)
                engine.SoundManager.play('buzz.ogg')
        else:
            TouchFeedback(event.pos, consts.COLOR_RED)
            engine.SoundManager.play('buzz.ogg')
            TextFeedback(event.pos, 'AMMO DEPLETED!', consts.COLOR_RED)

    def _onKeyDown(self, event):
        if consts.DEBUG:
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
                Missile.speedMul = consts.ULTRASPEED_MISSILE_MUL
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
            elif event.keystring == 's':
                self.addScore(5000)
                return True
            elif event.keystring == 'e':
                self.clouds.blink()
                return True

    def updateAmmoGauge(self):
        ammo = 0
        for t in Target.filter(Turret):
            ammo += t.getAmmo()

        fdammo = self.gameData['initialAmmo'] - ammo
        afv = 1 - float(fdammo) / self.gameData['initialAmmo']
        if afv < 0.2:
            self.__ammoGauge.setColor(consts.COLOR_RED)
        self.__ammoGauge.setFVal(afv)

    def enemyDestroyed(self, enemy, target=None):
        self.__enemiesGone += 1
        self.__enemiesGauge.setFVal(
                1 - float(self.__enemiesGone) /
                self.gameData['initialEnemies'])

        if target is None:
            self.addScore(consts.ENEMY_DESTROYED_SCORE)
            self.gameData['enemiesDestroyed'] += 1
        else:
            if not target.isDead and target.hit():
                TextFeedback(target.getHitPos(), 'BUSTED!', consts.COLOR_RED)
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
                not Explosion.filter(EmpExplosion)):
            Missile.speedMul = consts.ULTRASPEED_MISSILE_MUL
            self.__changeGameState(self.GAMESTATE_ULTRASPEED)

    def __spawnEnemies(self):
        if (self.__enemiesToSpawn and Target.objects and
                (self.__gameState == self.GAMESTATE_ULTRASPEED or
                random.randrange(0, 100) <= self.__wave)):
            origin = Point2D(random.randrange(0, app().size.x), 0)
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
        self.__resultHeader = widgets.GameWordsNode(alignment='center',
            fontsize=70, color='ff2222', parent=self)

        self.__resultsParagraph = widgets.GameWordsNode(
            pos=(app().size.x / 2, app().size.y / 2 - 40),
            alignment='center', fontsize=40, color='aaaaaa', parent=self)

        self.registerBgTrack('results.ogg')

    def _preTransIn(self):
        self.__resultHeader.text = 'Wave %d results' % (
                self.engine.getState('game').getLevel())
        self.__resultHeader.pos = (app().size.x / 2, app().size.y / 2)
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
            'Cities bonus: %d' % (len(Target.filter(City)) * consts.CITY_RESCUE_SCORE),
        ]

        if self.engine.getState('game').nukeFired:
            self.rows.append('EMP Missiles launched: %d' %
                    gameState.gameData['ammoFired'])
        else:
            self.rows.append(
                'EMP Missiles launched: %d (%d%% accuracy)' % (
                        gameState.gameData['ammoFired'],
                        self.__getAccuracy()))

        gameState.addScore(len(Target.filter(City)) * consts.CITY_RESCUE_SCORE)
        avg.EaseInOutAnim(self.__resultHeader, 'y', consts.RESULTS_ADDROW_DELAY / 2,
                app().size.y / 2,
                app().size.y / 2 - 140, False,
                consts.RESULTS_ADDROW_DELAY / 6, consts.RESULTS_ADDROW_DELAY / 4,
                None, self.__addResultRow).start()

    def returnToGame(self):
        self.engine.changeState('game')

    def __addResultRow(self):
        row = self.rows[0]
        self.rows.remove(row)
        self.__resultsParagraph.text += row + '<br/>'

        if self.rows:
            g_Player.setTimeout(consts.RESULTS_ADDROW_DELAY, self.__addResultRow)
        else:
            g_Player.setTimeout(consts.RESULTS_DELAY, self.returnToGame)

    def __getAccuracy(self):
        mfired = self.engine.getState('game').gameData['ammoFired']
        if mfired == 0:
            return 0
        else:
            return (float(self.engine.getState('game').gameData['enemiesDestroyed']) /
                    self.engine.getState('game').gameData['ammoFired'] * 100)


class GameOver(engine.FadeGameState):
    def _init(self):
        widgets.GameWordsNode(text='Game Over', pos=(app().size.x / 2,
                app().size.y / 2 - 80), alignment='center', fontsize=70,
                color='ff2222', parent=self)
        self.__score = widgets.GameWordsNode(pos=(app().size.x / 2,
                app().size.y / 2 + 20), alignment='center', fontsize=40,
                color='aaaaaa', parent=self)

    def _preTransIn(self):
        score = self.engine.getState('game').getScore()
        self.__score.text = 'Score: %d' % score

    def _postTransIn(self):
        db = app().scoreDatabase
        if not db.isFull() or db.data[-1].points < \
                self.engine.getState('game').getScore():
            g_Player.setTimeout(consts.GAMEOVER_DELAY / 2,
                lambda: self.engine.changeState('hiscore'))
        else:
            g_Player.setTimeout(consts.GAMEOVER_DELAY,
                    lambda: self.engine.changeState('start'))


class Hiscore(engine.FadeGameState):
    TIMEOUT = 8000
    def _init(self):
        widgets.GameWordsNode(text='New hiscore!',
                pos=(app().size.x / 2, 70), alignment='center', fontsize=70,
                color='ff2222', parent=self)

        self.__score = widgets.GameWordsNode(pos=(app().size.x / 2, 170),
                alignment='center', fontsize=40, color='aaaaaa', parent=self)

        self.__keyboard = widgets.Keyboard(self.__onKeyTouch, parent=self)
        self.__keyboard.pos = ((app().size.x - self.__keyboard.size.x) / 2,
                app().size.y - self.__keyboard.size.y - 100)

        self.__playerName = widgets.PlayerName(parent=self)
        self.__playerName.pos = ((app().size.x - self.__playerName.size.x) / 2,
                240)

        self.__timeout = None

    def _preTransIn(self):
        self.__score.text = 'Score: %d' % self.engine.getState('game').getScore()
        self.__playerName.reset()
        self.__resetTimeout()

    def __saveScore(self):
        name = self.__playerName.text
        if name == '':
            name = '???'

        app().scoreDatabase.addScore(
                engine.ScoreEntry(name, self.engine.getState('game').getScore()))

    def __clearTimeout(self):
        if self.__timeout is not None:
            g_Player.clearInterval(self.__timeout)

    def __resetTimeout(self):
        def fire():
            self.__timeout = None
            self.__saveScore()
            self.engine.changeState('start')

        self.__clearTimeout()
        self.__timeout = g_Player.setTimeout(self.TIMEOUT, fire)

    def __onKeyTouch(self, key):
        self.__resetTimeout()
        if key == '<':
            self.__playerName.delete()
        elif key == '#':
            self.__saveScore()
            self.__clearTimeout()
            self.engine.changeState('start')
        else:
            self.__playerName.addChar(key)

