#Copyright 2011 Dan Klinedinst
#
#This file is part of Gibson.
#
#Gibson is free software: you can redistribute it and/or modify it
#under the terms of the GNU General Public License as published by the
#Free Software Foundation, either version 3 of the License, or any
#later version.

#Gibson is distributed in the hope that it will be useful, but WITHOUT
#ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
#FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
#for more details.
#
#You should have received a copy of the GNU General Public License
#along with Gibson.  If not, see <http://www.gnu.org/licenses/>.

class SluggerBase():
    def __init__(self, panda, data):
        self.starting_position = (0, 0, 0)
        self.data = data
        self.panda = panda


    def createTunnel(self):
        raise "Not Implemented"

    def createSlug(self):
        raise "Not Implemented"