'''
        @ Josh Roy (thosehippos) thosehippos@protonmail.com)
        December 2017
        Generals.io Automated Client - 
'''

import logging
import random
from base import bot_base
from base.bot_base import _create_thread
from copy import deepcopy
import time
from collections import deque 
from Queue import PriorityQueue
from thosehipposBot import thosehipposBot

class PathNode(object):
        def __init__(self, tile, parent, value, turn, cityCount, pathDict):
                self.tile = tile
                self.parent = parent
                self.value = value
                self.turn = turn
                self.cityCount = cityCount
                self.pathDict = pathDict
        def __gt__(self, other):
                if (other == None):
                        return True
                return self.turn > other.turn
        def __lt__(self, other):
                if (other == None):
                        return True
                return self.turn < other.turn   



def dist(tileA, tileB):
        return abs(tileA.x - tileB.x) + abs(tileA.y - tileB.y)


def stringPath(pathNode):
        val = "[{}] ".format(pathNode.value) 
        while (pathNode != None):
                val = val + str(pathNode.tile.x) + "," + str(pathNode.tile.y) + " "
                pathNode = pathNode.parent
        return val              

def PathContains(node, x, y):
        return PathContainsCount(node, x, y) > 0


def GetTile(Map, x, y):
        if (x < 0 or x >= Map.cols or y < 0 or y >= Map.rows):
                return None
        return Map.grid[y][x]

        
                
# Show all logging
logging.basicConfig(level=logging.DEBUG)

######################### Move Making #########################
THREAD_COUNT = 6



class Move(object):
        def __init__(self, source, dest):
                self.source = source
                self.dest = dest
        def __gt__(self, other):
                if (other == None):
                        return True
                return self.source.army - self.dest.army > other.source.army - other.dest.army
        def __lt__(self, other):
                if (other == None):
                        return False
                return self.source.army - self.dest.army < other.source.army - other.dest.army
        def __eq__(self, other):
                if (None == other):
                        return False
                return self.source.army - self.dest.army == other.source.army - other.dest.army

hippoBot = thosehipposBot(THREAD_COUNT)

# Makes the move in the game
def make_move(currentBot, currentMap):
        global _bot, _map
        _bot = currentBot
        _map = currentMap
        hippoBot._bot = _bot
        hippoBot._map = _map

        command = currentBot.getLastCommand()   
        if (command == "-s"):
                return
        
        move = hippoBot.dummyMover()
        if (move != None):
                if not place_move(move.source, move.dest):
                        print("!!!!!!!!! {},{} -> {},{} was an illegal / bad move!!!!".format(move.source.x, move.source.y, move.dest.x, move.dest.y))
                        hippoBot.curPath = None
                        hippoBot.curPathPrio = -1
        return

class GeneralAverager(object):
        def __init__(self, map, playerIndex):
                self.x = -1
                self.y = -1
                self.player = playerIndex
                self.map = map

        def calculate():
                a = 0

def place_move(source, dest):
        moveHalf = False
        if _map.turn > 200:
                if source.isGeneral:
                        moveHalf = True
                elif source.isCity and _map.turn - source.turn_captured < 50:
                        moveHalf = True
        
        print("Placing move: {},{} to {},{}".format(source.x, source.y, dest.x, dest.y))
        return _bot.place_move(source, dest, move_half=moveHalf)

def make_primary_move():
        if not move_toward():
                move_outward()

######################### Move Outward #########################
def move_outward():
        for x in bot_base._shuffle(range(_map.cols)): # Check Each Square
                for y in bot_base._shuffle(range(_map.rows)):
                        source = _map.grid[y][x]

                        if (source.tile == _map.player_index and source.army >= 2 and source not in _path): # Find One With Armies
                                for dy, dx in _bot.toward_dest_moves(source):
                                        if (_bot.validPosition(x + dx,y + dy)):
                                                dest = _map.grid[y + dy][x + dx]
                                                if (dest.tile != _map.player_index and source.army > (dest.army + 1)) or (dest in _path): # Capture Somewhere New
                                                        place_move(source, dest)
                                                        return True
        return False

######################### Move Toward #########################
_path = []
def move_toward():
        # Find path from largest tile to closest target
        source = _bot.find_largest_tile(includeGeneral=True)
        target = _bot.find_closest_target(source)
        path = _bot.find_path(source=source, dest=target)

        army_total = 0
        for tile in path: # Verify can obtain every tile in path
                if (tile.tile == _map.player_index):
                        army_total += (tile.army - 1)
                elif (tile.army + 1 > army_total): # Cannot obtain tile, draw path from largest city to largest tile
                        source = _bot.find_city(includeGeneral=True)
                        target = _bot.find_largest_tile(notInPath=[source])
                        if (source and target and source != target):
                                path = _bot.find_path(source=source, dest=target)
                        break

        # Place Move
        _path = path
        _bot._path = path
        (move_from, move_to) = _bot.path_forward_moves(path)
        if (move_from != None):
                place_move(move_from, move_to)
                return True

        return False

######################### Main #########################

# Start Game
import startup
if __name__ == '__main__':
        startup.startup(make_move, "testbot")
