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

DEBUG = os.getenv('EMP_DEBUG', False)
ENABLE_PROFILING = os.getenv('EMP_PROFILE', False)

HISCORE_FILENAME = 'hiscore.dat'

ORIGINAL_SIZE = (1280, 800)

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
MAX_INSTANCE_SOUNDS = 10

INVALID_TARGET_Y_OFFSET = 100

CITY_RESCUE_SCORE = 800
CITIES = 3
ENEMY_DESTROYED_SCORE = 50

SOUND_FREQUENCY = 44100
SOUND_BUFFER_SIZE = 1024
SOUND_VOICES = 32
