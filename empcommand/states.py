#!/usr/bin/env python
# -*- coding: utf-8 -*-

# EMP Command: a missile command multitouch clone
# Copyright (c) 2010-2015 OXullo Intersecans <x@brainrapers.org>. All rights reserved.
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
import logging
import datetime

from libavg import avg, Point2D, player, app

from empcommand import VERSION

import engine
import consts
import widgets
import score
from gameobjs import *


logger = logging.getLogger(__name__)


class Start(engine.FadeGameState):
    def _init(self):
        im = avg.ImageNode(href='logo.png', parent=self)

        xfactor = engine.norm.size.x / im.getMediaSize().x / 2
        im.size = im.getMediaSize() * xfactor
        im.pos = (0, engine.norm.size.y - im.size.y)

        rightPane = avg.DivNode(pos=engine.norm.p((765, 90)), parent=self)
        
        self.__menu = widgets.Menu(onPlay=self.__onPlay, onAbout=self.__onAbout,
                onDiffChanged=self.__onDiffChanged, onQuit=self.__onQuit,
                size=engine.norm.p((350, 300)), parent=rightPane)

        self.__hiscoreTab = widgets.HiscoreTab(db=app.instance.mainDiv.scoreDatabase,
                pos=engine.norm.p((0, 350)), size=engine.norm.p((350, 270)),
                parent=rightPane)
        
        self.registerBgTrack('theme_start.ogg')
        
    def _resume(self):
        self.__hiscoreTab.refresh()
    
    def _preTransIn(self):
        self.__hiscoreTab.refresh()

    def _onKeyDown(self, event):
        self.__menu.onKeyDown(event)
        
        if consts.DEBUG:
            if event.keystring == 's':
                self.sequencer.changeState('game')
                return True
            if event.keystring == 'd':
                import time
                time.sleep(random.random())
                return True

    def _update(self, dt):
        self.__hiscoreTab.update(dt)
        self.__menu.update(dt)

    def __onPlay(self):
        self.sequencer.getState('game').setNewGame()
        self.sequencer.changeState('game')

    def __onAbout(self):
        self.sequencer.changeState('about')
    
    def __onDiffChanged(self, ndiff):
        app.instance.mainDiv.difficultyLevel = ndiff
        
    def __onQuit(self):
        player.stop()


class About(engine.FadeGameState):
    def _init(self):
        im = avg.ImageNode(href='logo.png', parent=self)
        xfactor = engine.norm.size.x / im.getMediaSize().x / 2
        im.size = im.getMediaSize() * xfactor
        
        about = widgets.VLayout(interleave=10, width=600, pos=engine.norm.p((580, 300)),
                parent=self)
        about.add(widgets.GameWordsNode(text='EMPCommand', color=consts.COLOR_BLUE,
                fontsize=60))
        about.add(widgets.GameWordsNode(
                text='VERSION: %s' % VERSION,
                color=consts.COLOR_BLUE, fontsize=8))

        year = datetime.date.today().year
        about.add(widgets.GameWordsNode(text='© 2010-%d OXullo Intersecans' % year,
                color='ffffff', fontsize=25))
        about.add(widgets.GameWordsNode(text='http://www.brainrapers.org/empcommand/',
                color=consts.COLOR_RED, fontsize=18))
        about.add(widgets.GameWordsNode(
                text='''Yet another Missile Command ® clone, fully employing modern
                multitouch controllers.<br/>Enemies must be defeated with fierce touches
                on your multitouch surface, but be aware of timings and ammo!<br/><br/>
                Bonus powerups are given for multiple kills with single 
                missiles:<br/><br/> * AMMO
                powerup (3 enemies in one shot): turret ammo will be refilled<br/>
                 * NUKE powerup (4 enemies or more): the designated turret will
                launch a super powerful missile that will wipe out most of the
                enemies<br/><br/>Powerups can be deployed with a drag&amp;drop to one of
                the living turrets.<br/>Keep cities from being destroyed if you want to
                raise up your score and consider that once a turret has been hit for three
                times, it's gone, along with its ammo.''',
                width=engine.norm.x(600), color='ffffff', fontsize=12))
                
        about.add(widgets.GameWordsNode(
                text='This game is based on libavg (http://www.libavg.de)',
                color=consts.COLOR_RED, fontsize=16), offset=10)
        
        avg.ImageNode(href='enmy_sky.png', size=(engine.norm.size.x, engine.norm.y(300)),
                pos=(0, engine.norm.size.y - engine.norm.y(300)), angle=math.pi,
                opacity=0.2, parent=self)
        
        self.registerBgTrack('theme_about.ogg', maxVolume=0.5)

    def _onTouch(self, event):
        engine.SoundManager.play('click.ogg')
        self.sequencer.changeState('start')
    
    def _onKeyDown(self, event):
        engine.SoundManager.play('click.ogg')
        self.sequencer.changeState('start')
        return True


class Game(engine.FadeGameState):
    GAMESTATE_INITIALIZING = 'INIT'
    GAMESTATE_PLAYING = 'PLAY'
    GAMESTATE_ULTRASPEED = 'ULTRA'

    def _init(self):
        # Sky
        avg.ImageNode(href='enmy_sky.png', size=(engine.norm.size.x, engine.norm.y(300)),
                opacity=0.3, parent=self)
        self.clouds = widgets.Clouds(maxOpacity=0.4, size=(engine.norm.size.x,
                engine.norm.y(600)), parent=self)
        EnemyExplosion.registerCallback(self.clouds.blink)
        
        # Allied ground
        a = engine.norm.x(5)
        b = engine.norm.y(10)
        c = engine.norm.x(30)
        d = engine.norm.y(5)
        ito = engine.norm.y(consts.INVALID_TARGET_Y_OFFSET)
        polpos = (
            (-a, engine.norm.size.y - ito + b),
            (c, engine.norm.size.y - ito),
            (engine.norm.size.x - c, engine.norm.size.y - ito),
            (engine.norm.size.x + a, engine.norm.size.y - ito + b),
            (engine.norm.size.x + a, engine.norm.size.y + d),
            (-a, engine.norm.size.y + d),
        )
        
        avg.PolygonNode(
                pos=polpos,
                color=consts.COLOR_BLUE,
                fillcolor=consts.COLOR_BLUE,
                opacity=0.3,
                fillopacity=0.05,
                parent=self
                )
        
        self.explGround = avg.PolygonNode(
                pos=polpos,
                fillcolor=consts.COLOR_RED,
                opacity=0,
                fillopacity=0,
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
        self.__enemiesSpawnTimeline = []
        self.__enemiesGone = 0
        self.__gameState = self.GAMESTATE_INITIALIZING
        self.__wave = 0

        engine.SoundManager.allocate('buzz.ogg')

        self.__scoreText = widgets.GameWordsNode(text='0',
                pos=(engine.norm.size.x / 2, engine.norm.y(100)),
                alignment='center', fontsize=50, opacity=0.5, parent=self)
        self.__teaser = widgets.GameWordsNode(text='',
                pos=(engine.norm.size.x / 2, engine.norm.y(300)),
                alignment='center', fontsize=70, opacity=0.5, parent=self)

        self.__ammoGauge = widgets.Gauge(consts.COLOR_BLUE,
                widgets.Gauge.LAYOUT_VERTICAL,
                pos=(engine.norm.x(20),
                    engine.norm.size.y - engine.norm.y(consts.INVALID_TARGET_Y_OFFSET) - \
                        engine.norm.y(350)),
                size=(engine.norm.x(15), engine.norm.y(300)), parent=self)
        self.__ammoGauge.addLabel('AMMO')
        self.__ammoGauge.setOpacity(0.3)

        self.__enemiesGauge = widgets.Gauge(consts.COLOR_RED,
                widgets.Gauge.LAYOUT_VERTICAL,
                pos=(engine.norm.size.x - engine.norm.x(35), engine.norm.size.y - \
                    consts.INVALID_TARGET_Y_OFFSET - engine.norm.y(350)),
                size=(engine.norm.x(15), engine.norm.y(300)), parent=self)
        self.__enemiesGauge.addLabel('ENMY')
        self.__enemiesGauge.setOpacity(0.3)
        
        self.__lowAmmoNotified = False

        self.registerBgTrack('theme_game.ogg', maxVolume=0.3)

        if consts.DEBUG:
            self.__debugArea = widgets.GameWordsNode(pos=(10, 10), size=(300, 600),
                fontsize=8, color='ffffff', opacity=0.7, parent=self)
        
        self.__quitSwitch = widgets.QuitSwitch(cb=self.__onExit,
                pos=engine.norm.p((1076, 10)), parent=self)

    def _preTransIn(self):
        self.reset()

    def _postTransIn(self):
        self.nextWave()
        widgets.CrossHair.warningy = engine.norm.size.y - \
                engine.norm.y(consts.INVALID_TARGET_Y_OFFSET)

    def _preTransOut(self):
        self.__changeGameState(self.GAMESTATE_INITIALIZING)
        widgets.CrossHair.warningy = -1

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
        
        self.__quitSwitch.reset()
        self.__lowAmmoNotified = False

    def setNewGame(self):
        self.__wave = 0
        self.setScore(0)

    def nextWave(self):
        Missile.speedMul = 1 + (app.instance.mainDiv.difficultyLevel - 1) * consts.SPEEDMUL_OFFSET_LEVEL
        self.nukeFired = False
        self.__wave += 1
        
        nenemies =  int(self.__wave * consts.ENEMIES_WAVE_MULT * \
                (1 + app.instance.mainDiv.difficultyLevel * 0.2))
        
        self.__createSpawnTimeline(nenemies)
        self.__enemiesGone = 0
        self.gameData['initialEnemies'] = nenemies

        slots = [Point2D(x * engine.norm.x(consts.SLOT_WIDTH), engine.norm.size.y - \
                engine.norm.y(60))
                    for x in xrange(1,
                        int(engine.norm.size.x/engine.norm.x(consts.SLOT_WIDTH) + 1))]

        random.shuffle(slots)

        self.gameData['initialAmmo'] = int(nenemies * consts.AMMO_ENEMIES_MULT)
        self.gameData['initialCities'] = consts.CITIES

        for i in xrange(0, consts.TURRETS_AMOUNT):
            Turret(slots.pop(), float(self.gameData['initialAmmo']) /
                    consts.TURRETS_AMOUNT)

        for c in xrange(0, self.gameData['initialCities']):
            City(slots.pop())

        self.__ammoGauge.setColor(consts.COLOR_BLUE)
        self.__ammoGauge.setFVal(1)
        self.__enemiesGauge.setFVal(1)

        self.playTeaser('Wave %d' % self.__wave)
        self.__waveTimer = player.getFrameTime()
        self.__changeGameState(self.GAMESTATE_PLAYING)
        logger.info('Entering wave %d: %s' % (self.__wave, str(self.gameData)))

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
                        ('dt=%03dms ar=%1.2f' % (dt,
                            ammoRatio)) + '<br/>' +
                        str(self.gameData) + '<br/>' +
                        str(Target.objects) + '<br/>' +
                        '<br/>'.join(map(str, Missile.filter(Enemy))) + '<br/>' +
                        '<br/>'.join(map(str, Missile.filter(TurretMissile))))

            Missile.update(dt)
            self.__checkGameStatus()
            self.__spawnEnemy()

    def _onTouch(self, event):
        turrets = filter(lambda o: o.hasAmmo(), Target.filter(Turret))
        if turrets:
            ito = engine.norm.y(consts.INVALID_TARGET_Y_OFFSET)
            if event.pos.y < engine.norm.size.y - ito:
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
                engine.SoundManager.play('buzz.ogg', volume=0.5)
        else:
            TouchFeedback(event.pos, consts.COLOR_RED)
            engine.SoundManager.play('buzz.ogg', volume=0.5)
            TextFeedback(event.pos, 'AMMO DEPLETED!', consts.COLOR_RED)

    def _onKeyDown(self, event):
        if consts.DEBUG:
            if event.keystring == 'x':
                self.sequencer.changeState('gameover')
                return True
            elif event.keystring == 'r':
                self.sequencer.changeState('results')
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
                self.sequencer.changeState('game')
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
            elif event.keystring == '1':
                self.sequencer.changeState('hiscore')
                return True
            elif event.keystring == 'h':
                self.reset()
                self.nextWave()
                return True

    def updateAmmoGauge(self):
        ammo = 0
        for t in Target.filter(Turret):
            ammo += t.getAmmo()

        fdammo = self.gameData['initialAmmo'] - ammo
        afv = 1 - float(fdammo) / self.gameData['initialAmmo']
        if afv < 0.2 and not self.__lowAmmoNotified:
            self.__ammoGauge.setColor(consts.COLOR_RED)
            engine.SoundManager.play('low_ammo.ogg', volume=0.5)
            TextFeedback(self.__ammoGauge.pos + self.__ammoGauge.size / 2 + \
                    Point2D(engine.norm.x(250), 0),
                    'Low ammo!', consts.COLOR_RED)
            self.__lowAmmoNotified = True
        self.__ammoGauge.setFVal(afv)

    def enemyDestroyed(self, enemy, target=None):
        self.__enemiesGone += 1
        self.__enemiesGauge.setFVal(
                1 - float(self.__enemiesGone) /
                self.gameData['initialEnemies'])

        if target is None:
            self.addScore(consts.ENEMY_DESTROYED_SCORE *
                    (1 + app.instance.mainDiv.difficultyLevel * 0.3))
            self.gameData['enemiesDestroyed'] += 1
        else:
            avg.EaseInOutAnim(self.explGround, 'fillopacity', 200,
                    0.2, 0, 0, 200).start()
                        
            if not target.isDead and target.hit():
                TextFeedback(target.getHitPos(), 'BUSTED!', consts.COLOR_RED)
                # If we lose a turret, ammo stash sinks with it
                self.updateAmmoGauge()

    def __getWaveTime(self):
        return player.getFrameTime() - self.__waveTimer
        
    def __createSpawnTimeline(self, nenemies):
        self.__enemiesSpawnTimeline = []
        avgSpawnTime = consts.WAVE_DURATION * 1000.0 / nenemies
        absJitter = int(avgSpawnTime * consts.ENEMIES_SPAWNER_JITTER_FACTOR)
        tm = consts.WAVE_PREAMBLE * 1000
        
        for i in xrange(nenemies):
            self.__enemiesSpawnTimeline.append(tm)
            tm += avgSpawnTime + random.randrange(-absJitter, absJitter)

        logger.info('Avg spawn time: %d Abs jitter: %d' % (avgSpawnTime, absJitter))

    def __checkGameStatus(self):
        if self.__gameState not in (self.GAMESTATE_PLAYING, self.GAMESTATE_ULTRASPEED):
            return
            
        # Game end
        if not Target.filter(City):
            self.sequencer.changeState('gameover')

        # Wave end
        if not self.__enemiesSpawnTimeline and not Missile.filter(Enemy):
            logger.info('Wave ended')
            self.sequencer.changeState('results')

        # Switch to ultraspeed if there's nothing the player can do
        if (self.__ammoGauge.getFVal() == 0 and
                not Missile.filter(TurretMissile) and
                not Explosion.filter(EmpExplosion) and
                self.__gameState == self.GAMESTATE_PLAYING):
            Missile.speedMul = consts.ULTRASPEED_MISSILE_MUL
            self.__changeGameState(self.GAMESTATE_ULTRASPEED)

    def __spawnEnemy(self):
        if (self.__enemiesSpawnTimeline and Target.objects and
                (self.__gameState == self.GAMESTATE_ULTRASPEED or
                self.__enemiesSpawnTimeline[0] < self.__getWaveTime())):
            self.__enemiesSpawnTimeline.pop(0)
            origin = Point2D(random.randrange(0, engine.norm.size.x), 0)
            target = random.choice(Target.objects)
            Enemy(origin, target, self.__wave)

    def __teaserTimer(self):
        player.setTimeout(1000, lambda: avg.fadeOut(self.__teaser, 3000))

    def __changeGameState(self, newState):
        logger.info('Gamestate %s -> %s' % (self.__gameState, newState))
        self.__gameState = newState

    def __onExit(self):
        self.sequencer.changeState('start')


class Results(engine.FadeGameState):
    def _init(self):
        self.__resultHeader = widgets.GameWordsNode(alignment='center',
            fontsize=70, color='ff2222', parent=self)

        self.__resultsParagraph = widgets.GameWordsNode(
            pos=(engine.norm.size.x / 2, engine.norm.size.y / 2 - 40),
            alignment='center', fontsize=40, color='aaaaaa', parent=self)

        self.registerBgTrack('theme_results.ogg')

    def _preTransIn(self):
        self.__resultHeader.text = 'Wave %d results' % (
                self.sequencer.getState('game').getLevel())
        self.__resultHeader.pos = (engine.norm.size.x / 2, engine.norm.size.y / 2)
        self.__resultsParagraph.text = ''

    def _postTransIn(self):
        gameState = self.sequencer.getState('game')
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

        if self.sequencer.getState('game').nukeFired:
            self.rows.append('EMP Missiles launched: %d' %
                    gameState.gameData['ammoFired'])
        else:
            self.rows.append(
                'EMP Missiles launched: %d (%d%% accuracy)' % (
                        gameState.gameData['ammoFired'],
                        self.__getAccuracy()))

        gameState.addScore(len(Target.filter(City)) * consts.CITY_RESCUE_SCORE *
                (1 + app.instance.mainDiv.difficultyLevel * 0.3))
                
        avg.EaseInOutAnim(self.__resultHeader, 'y', consts.RESULTS_ADDROW_DELAY / 2,
                engine.norm.size.y / 2,
                engine.norm.size.y / 2 - 140, False,
                consts.RESULTS_ADDROW_DELAY / 6, consts.RESULTS_ADDROW_DELAY / 4,
                None, self.__addResultRow).start()

    def returnToGame(self):
        self.sequencer.changeState('game')

    def __addResultRow(self):
        row = self.rows[0]
        self.rows.remove(row)
        self.__resultsParagraph.text += row + '<br/>'

        if self.rows:
            player.setTimeout(consts.RESULTS_ADDROW_DELAY, self.__addResultRow)
        else:
            player.setTimeout(consts.RESULTS_DELAY, self.returnToGame)

    def __getAccuracy(self):
        mfired = self.sequencer.getState('game').gameData['ammoFired']
        if mfired == 0:
            return 0
        else:
            return (float(self.sequencer.getState('game').gameData['enemiesDestroyed']) /
                    self.sequencer.getState('game').gameData['ammoFired'] * 100)


class GameOver(engine.FadeGameState):
    def _init(self):
        widgets.GameWordsNode(text='Game Over', pos=(engine.norm.size.x / 2,
                engine.norm.size.y / 2 - 80), alignment='center', fontsize=70,
                color='ff2222', parent=self)
        self.__score = widgets.GameWordsNode(pos=(engine.norm.size.x / 2,
                engine.norm.size.y / 2 + 20), alignment='center', fontsize=40,
                color='aaaaaa', parent=self)

    def _preTransIn(self):
        score = self.sequencer.getState('game').getScore()
        self.__score.text = 'Score: %d' % score

    def _postTransIn(self):
        db = app.instance.mainDiv.scoreDatabase
        if not db.isFull() or db.data[-1].points < \
                self.sequencer.getState('game').getScore():
            player.setTimeout(consts.GAMEOVER_DELAY / 2,
                lambda: self.sequencer.changeState('hiscore'))
        else:
            player.setTimeout(consts.GAMEOVER_DELAY,
                    lambda: self.sequencer.changeState('start'))


class Hiscore(engine.FadeGameState):
    TIMEOUT = 8000
    def _init(self):
        widgets.GameWordsNode(text='New hiscore!',
                pos=(engine.norm.size.x / 2, engine.norm.y(70)), alignment='center', fontsize=70,
                color='ff2222', parent=self)

        self.__score = widgets.GameWordsNode(pos=(engine.norm.size.x / 2, engine.norm.y(170)),
                alignment='center', fontsize=40, color='aaaaaa', parent=self)

        self.__keyboard = widgets.Keyboard(
                keySize=engine.norm.y(60),
                padding=engine.norm.x(15),
                cb=self.__onKeyTouch, parent=self)
        self.__keyboard.pos = ((engine.norm.size.x - self.__keyboard.size.x) / 2,
                engine.norm.size.y - self.__keyboard.size.y - engine.norm.y(100))

        self.__playerName = widgets.PlayerName(size=engine.norm.p((450, 150)),
                parent=self)
        self.__playerName.pos = ((engine.norm.size.x - self.__playerName.size.x) / 2,
                engine.norm.y(240))

        self.__timeout = None

    def _preTransIn(self):
        self.__score.text = 'Score: %d' % self.sequencer.getState('game').getScore()
        self.__playerName.reset()
        self.__resetTimeout()

    def _onKeyDown(self, event):
        key = event.keystring.upper()
        if key in ('#', '<'):
            return False
        
        if key == 'RETURN':
            key = '#'
        elif key == 'BACKSPACE':
            key = '<'
            
        if key in self.__keyboard.allowedKeys:
            self.__onKeyTouch(key)
            return True
        
    def __saveScore(self):
        name = self.__playerName.text
        if name == '':
            name = '???'

        app.instance.mainDiv.scoreDatabase.addScore(
                score.ScoreEntry(name, self.sequencer.getState('game').getScore()))

    def __clearTimeout(self):
        if self.__timeout is not None:
            player.clearInterval(self.__timeout)

    def __resetTimeout(self):
        def fire():
            self.__timeout = None
            self.__saveScore()
            self.sequencer.changeState('start')

        self.__clearTimeout()
        self.__timeout = player.setTimeout(self.TIMEOUT, fire)

    def __onKeyTouch(self, key):
        self.__resetTimeout()
        if key == '<':
            engine.SoundManager.play('selection.ogg', volume=0.5)
            self.__playerName.delete()
        elif key == '#':
            engine.SoundManager.play('click.ogg')
            self.__saveScore()
            self.__clearTimeout()
            self.sequencer.changeState('start')
        else:
            engine.SoundManager.play('selection.ogg', volume=0.5)
            self.__playerName.addChar(key)

