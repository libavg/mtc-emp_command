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

from libavg import persist

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
        self.__ds = persist.UserPersistentData(appName='empcommand', fileName='hiscore',
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
