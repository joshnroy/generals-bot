'''
        @ Harris Christiansen (Harris@HarrisChristiansen.com)
        January 2016
        Generals.io Automated Client - https://github.com/harrischristiansen/generals-bot
        Map: Objects for representing Generals IO Map and Tiles
'''
import json
TILE_EMPTY = -1
TILE_MOUNTAIN = -2
TILE_FOG = -3
TILE_OBSTACLE = -4

_REPLAY_URLS = {
        'na': "http://generals.io/replays/",
        'eu': "http://eu.generals.io/replays/",
}

class Player(object):
        def __init__(self, player_index):
                self.cities = []
                self.general = None
                self.index = player_index
                self.stars = 0
                self.score = 0
                self.tileCount = 0
                self.standingArmy = 0
                self.cityCount = 1
                self.cityLostTurn = 0
                self.cityGainedTurn = 0
                self.delta25tiles = 0
                self.delta25score = 0
                self.dead = False
                self.capturedBy = None
                self.knowsKingLocation = False

class Map(object):
        def __init__(self, start_data, data):
                # Start Data
                self._start_data = start_data
                self.player_index = start_data['playerIndex']                                                                   # Integer Player Index
                self.teammate_index = -10                                               #TODO TEAMMATE
                self.usernames = start_data['usernames']                                                                                # List of String Usernames
                self.replay_url = _REPLAY_URLS["na"] + start_data['replay_id']                                  # String Replay URL # TODO: Use Client Region
                self.players = [Player(x) for x in range(len(self.usernames))]
                self.ekBot = None
                
                # First Game Data
                self._applyUpdateDiff(data)
                self.rows = self.rows                                                                                                                   # Integer Number Grid Rows
                self.cols = self.cols                                                                                                                   # Integer Number Grid Cols
                self.grid = [[Tile(x,y) for x in range(self.cols)] for y in range(self.rows)]   # 2D List of Tile Objects
                self.updateTurnGrid = [[int for x in range(self.cols)] for y in range(self.rows)]       # 2D List of Tile Objects
                self.turn = data['turn']                                                                                                                # Integer Turn # (1 turn / 0.5 seconds)
                self.cities = []                                                                                                                                # List of City Tiles
                self.generals = [ None for x in range(8) ]                                                                              # List of 8 Generals (None if not found)
                self._setGenerals()
                self.stars = []                                                                                                                                 # List of Player Star Ratings
                self.scores = self._getScores(data)                                                                                             # List of Player Scores
                self.complete = False                                                                                                                   # Boolean Game Complete
                self.result = False                                                                                                                             # Boolean Game Result (True = Won)
                self.scoreHistory = [None for i in range(25)]
                self.remainingPlayers = 0
                
                
        def updatePlayerInformation(self):
                cityCounts = [0 for i in range(len(self.players))]
                for player in self.players:
                        #print("player {}".format(player.index))
                        player.stars = self.stars[player.index]
                        player.score = self.scores[player.index]['total']
                        player.tileCount = self.scores[player.index]['tiles']
                        player.standingArmy = self.scores[player.index]['total'] - self.scores[player.index]['tiles']
                        
                
                last = self.scoreHistory[len(self.scoreHistory) - 1]
                earliest = last
                for i in range(len(self.scoreHistory) - 2, 0, -1):
                        turn = self.turn - i
                        scores = self.scoreHistory[i]
                        #print("turn {}".format(turn))
                        if (earliest == None):
                                earliest = scores
                        if (last != None):
                                for j, player in enumerate(self.players):
                                        score = scores[j]
                                        lastScore = last[j]
                                        tileDelta = score['tiles'] - lastScore['tiles']
                                        
                                        #print("player {} delta {}".format(player.index, delta))
                                        if (tileDelta >= 0 and turn % 50 != 0): #ignore army bonus turns                                        
                                                delta = score['total'] - lastScore['total']
                                                if (delta > 0):
                                                        cityCounts[j] = max(delta, cityCounts[j])               
                        last = scores
                self.remainingPlayers = 0
                for i, player in enumerate(self.players):
                        if not player.dead:
                                if player.cityCount < cityCounts[i]:
                                        player.cityCount = cityCounts[i]
                                        player.cityGainedTurn = self.turn
                                if player.cityCount > cityCounts[i] and cityCounts[i] > 0:
                                        player.cityCount = cityCounts[i]
                                        player.cityLostTurn = self.turn
                                if (earliest != None):
                                        player.delta25score = self.players[i].score - earliest[i]['total']
                                        player.delta25tiles = self.players[i].tileCount - earliest[i]['tiles']
                                if (self.scores[i]['dead'] == True):
                                        player.dead = True
                                else:
                                        self.remainingPlayers += 1

        def update(self, data):
                if self.complete: # Game Over - Ignore Empty Board Updates
                        return self
                oldTiles = self._tile_grid
                oldArmy = self._army_grid

                self._applyUpdateDiff(data)
                self.scores = self._getScores(data)
                for i in range(len(self.scoreHistory) - 1, 0, -1):
                        #print("scoreHistory updated: {}".format(i))
                        self.scoreHistory[i] = self.scoreHistory[i - 1]
                self.scoreHistory[0] = self.scores
                self.turn = data['turn']
                self.updatePlayerInformation()

                armyMovedGrid = [[bool for x in range(self.cols)] for y in range(self.rows)]
                #if (self.turn % 50 == 0):
                        #ignore rate change

                #with open("C:\Temp\lastDiff" + str(self.turn) + '.json', 'w') as outfile:
                #       json.dump(data, outfile)
                #with open('C:\Temp\stars.json', 'w') as outfile:
                #       json.dump(self.stars, outfile)

                for x in range(self.cols): # Update Each Tile
                        for y in range(self.rows):
                                #if (self._tile_grid[y][x] != oldTiles[y][x]):
                                        #tile changed ownership or visibility
                                tile_type = self._tile_grid[y][x]
                                army_count = self._army_grid[y][x]
                                isCity = (y,x) in self._visible_cities
                                isGeneral = (y,x) in self._visible_generals
                                
                                armyMovedGrid[y][x] = self.grid[y][x].update(self, tile_type, army_count, isCity, isGeneral)
                
                for x in range(self.cols): # Make assumptions about unseen tiles
                        for y in range(self.rows):
                                curTile = self.grid[y][x]
                                if (armyMovedGrid[y][x]):                                       
                                        #look for candidate tiles that army may have come from
                                        bestCandTile = None
                                        bestCandValue = -1
                                        if (x - 1 > 0): #examine left
                                                candidateTile = self.grid[y][x - 1]
                                                candValue = evaluateTileDiffs(curTile, candidateTile)
                                                if (candValue > bestCandValue):
                                                        bestCandValue = candValue
                                                        bestCandTile = candidateTile
                                        if (x + 1 < self.cols): #examine right
                                                candidateTile = self.grid[y][x + 1]
                                                candValue = evaluateTileDiffs(curTile, candidateTile)
                                                if (candValue > bestCandValue):
                                                        bestCandValue = candValue
                                                        bestCandTile = candidateTile
                                        if (y - 1 > 0): #examine top
                                                candidateTile = self.grid[y - 1][x]
                                                candValue = evaluateTileDiffs(curTile, candidateTile)
                                                if (candValue > bestCandValue):
                                                        bestCandValue = candValue
                                                        bestCandTile = candidateTile
                                        if (y + 1 < self.rows): #examine bottom
                                                candidateTile = self.grid[y + 1][x]
                                                candValue = evaluateTileDiffs(curTile, candidateTile)
                                                if (candValue > bestCandValue):
                                                        bestCandValue = candValue
                                                        bestCandTile = candidateTile

                                        if (bestCandTile != None):
                                                armyMovedGrid[bestCandTile.y][bestCandTile.x] = False
                                                armyMovedGrid[y][x] = False     
                                                if (curTile.player == -1):
                                                        curTile.player = bestCandTile.player
                                                curTile.delta.fromTile = bestCandTile
                                                bestCandTile.delta.toTile = curTile
                                if (not curTile.isvisible() and (curTile.isCity or curTile.isGeneral) and curTile.player >= 0 and self.turn % 2 == 0 and self.turn - curTile.lastSeen < 75):
                                        curTile.army += 1
                                if (not curTile.isvisible() and curTile.player >= 0 and self.turn % 50 == 0):
                                        curTile.army += 1
                                        

                return self

        def updateResult(self, result):
                self.complete = True
                self.result = result == "game_won"
                return self

        def _getScores(self, data):
                scores = {s['i']: s for s in data['scores']}
                scores = [scores[i] for i in range(len(scores))]

                if 'stars' in data:
                        self.stars[:] = data['stars']

                return scores

        def _applyUpdateDiff(self, data):
                if not '_map_private' in dir(self):
                        self._map_private = []
                        self._cities_private = []
                #TODO update map prediction
                _apply_diff(self._map_private, data['map_diff'])
                _apply_diff(self._cities_private, data['cities_diff'])
                
                

                # Get Number Rows + Columns
                self.rows, self.cols = self._map_private[1], self._map_private[0]

                # Create Updated Tile Grid
                self._tile_grid = [[self._map_private[2 + self.cols * self.rows + y * self.cols + x] for x in range(self.cols)] for y in range(self.rows)]
                # Create Updated Army Grid
                self._army_grid = [[self._map_private[2 + y * self.cols + x] for x in range(self.cols)] for y in range(self.rows)]
                
                # Update Visible Cities
                self._visible_cities = [(c // self.cols, c % self.cols) for c in self._cities_private] # returns [(y,x)]

                # Update Visible Generals
                self._visible_generals = [(-1, -1) if g == -1 else (g // self.cols, g % self.cols) for g in data['generals']] # returns [(y,x)]

        def _setGenerals(self):
                for i, general in enumerate(self._visible_generals):
                        if general[0] != -1:
                                self.generals[i] = self.grid[general[0]][general[1]]

def evaluateTileDiffs(tile, candidateTile):
        #both visible
        if (tile.isvisible() and candidateTile.isvisible()):
                return evaluateDualVisibleTileDiffs(tile, candidateTile)
        if (tile.isvisible() and not candidateTile.isvisible()):
                return evaluateMoveFromFog(tile, candidateTile)
        if (not tile.isvisible()):
                #print("evaluating fog island. friendlyCaptured: " + str(tile.delta.friendlyCaptured))
                return evaluateIslandFogMove(tile, candidateTile)
        return -100
        
def evaluateDualVisibleTileDiffs(tile, candidateTile):
        if (tile.delta.oldOwner == tile.delta.newOwner and candidateTile.delta.oldOwner == candidateTile.delta.newOwner and candidateTile.player == tile.player):
                return evaluateSameOwnerMoves(tile, candidateTile)
        if (tile.delta.oldOwner == -1 and candidateTile.delta.oldOwner == candidateTile.delta.newOwner and candidateTile.player == tile.player):
                return evaluateSameOwnerMoves(tile, candidateTile)
        #return evaluateSameOwnerMoves(tile, candidateTile)
        return -100

def evaluateMoveFromFog(tile, candidateTile):
        if (tile.delta.oldOwner == tile.delta.newOwner):
                return -100
        candidateDelta = candidateTile.army + tile.delta.armyDelta
        if (candidateDelta >= 0 and candidateDelta <= 2):
                candidateTile.army = 1
                return 100
        halfDelta = (candidateTile.army / 2) + tile.delta.armyDelta
        if (halfDelta >= 0 and halfDelta <= 2):
                return 50
        return -100

def evaluateIslandFogMove(tile, candidateTile):
        print(str(tile.army) + " : " + str(candidateTile.army))
        if ((candidateTile.isvisible() and tile.army + candidateTile.delta.armyDelta < -1 and candidateTile.player != -1)):
                tile.player = candidateTile.player
                tile.delta.newOwner = candidateTile.player
                tile.army = 0 - candidateTile.delta.armyDelta - tile.army
                candidateTile.army = 1
                return 50
        if (tile.army - candidateTile.army < -1 and candidateTile.player != -1):
                tile.player = candidateTile.player
                tile.delta.newOwner = candidateTile.player
                tile.army = candidateTile.army - tile.army - 1
                candidateTile.army = 1
                return 30
        return -100


def evaluateSameOwnerMoves(tile, candidateTile):
        if (tile.delta.armyDelta > 0): 
                delta = tile.delta.armyDelta + candidateTile.delta.armyDelta
                if (delta == 0):
                        return 100
                if (delta <= 2 and delta >= 0):
                        return 50       
        return -100

class TileDelta(object):
        def __init__(self, x, y):
                # Public Properties
                self.x = x                                      # Integer X Coordinate
                self.y = y                                      # Integer Y Coordinate

                self.oldOwner = -1
                self.newOwner = -1
                self.lostSight = False
                self.friendlyCaptured = False
                self.armyDelta = 0
                self.fromTile = None
                self.toTile = None
                

class Tile(object):
        def __init__(self, x, y, tile = TILE_EMPTY, army = 0, isCity = False, isGeneral = False, player = -1, mountain = False, turnCapped = 0):
                # Public Properties
                self.x = x                                      # Integer X Coordinate
                self.y = y                                      # Integer Y Coordinate
                self.tile = tile                # Integer Tile Type (TILE_OBSTACLE, TILE_FOG, TILE_MOUNTAIN, TILE_EMPTY, or
                                        # player_ID)
                self.turn_captured = turnCapped         # Integer Turn Tile Last Captured
                self.army = army                                # Integer Army Count
                self.isCity = isCity                    # Boolean isCity
                self.isGeneral = isGeneral              # Boolean isGeneral
                self.player = player
                self.visible = False
                self.discovered = False
                self.lastSeen = -1
                self.mountain = mountain
                self.delta = TileDelta(x, y)

        def __repr__(self):
                return "(%d,%d) %d (%d)" %(self.x, self.y, self.tile, self.army)

        '''def __eq__(self, other):
                        return (other != None and self.x==other.x and self.y==other.y)'''

        def __lt__(self, other):
                        return self.army < other.army
        
        def tileToString(self, tile):
                if (tile == TILE_EMPTY):
                        return "Empty"
                elif (tile == TILE_FOG):
                        return "Fog"
                elif (tile == TILE_MOUNTAIN):
                        return "Mountain"
                elif (tile == TILE_OBSTACLE):
                        return "Obstacle"
                return "Player " + str(tile)
        
        
        
        def isvisible(self):
                return self.visible

        def ismountain(self):
                return self.mountain

        def isobstacle(self):
                return self.tile == TILE_OBSTACLE and not self.isCity

        def update(self, map, tile, army, isCity=False, isGeneral=False):
                #if (self.tile < 0 or tile >= 0 or (tile < TILE_MOUNTAIN and self.tile == map.player_index)): # Remember Discovered Tiles
                #       if (tile >= 0 and self.tile != tile):                           
                #               if (self.player != tile):
                #                       self.turn_captured = map.turn
                #                       self.player = tile
                #                       print("Tile " + str(self.x) + "," + str(self.y) + " captured by player " + str(tile))
                #       if (self.tile != tile): 
                #               print("Tile " + str(self.x) + "," + str(self.y) + " from " + self.tileToString(self.tile) + " to " + self.tileToString(tile))
                #               self.tile = tile
                #               if (tile == TILE_MOUNTAIN):
                #                       self.mountain = True
                
                if (tile >= TILE_MOUNTAIN):
                        self.discovered = True
                        self.lastSeen = map.turn
                        self.visible = True
                self.delta = TileDelta(self.x, self.y)
                armyMovedHere = False
                
                self.delta.oldOwner = self.player
                
                
                        
                if (self.tile != tile): # tile changed
                        if (tile < TILE_MOUNTAIN and self.discovered): #lost sight of tile. 
                                self.delta.lostSight = True
                                self.lastSeen = map.turn - 1
                                self.visible = False
                                
                                if (self.player == map.player_index or self.player == map.teammate_index): 
                                        # we lost the tile
                                        # TODO Who might have captured it? for now set to unowned.
                                        self.delta.friendlyCaptured = True
                                        armyMovedHere = True
                                        self.player = -1
                        elif (tile == TILE_MOUNTAIN):
                                self.mountain = True
                        elif (tile >= 0):
                                self.player = tile
                                
                        self.tile = tile
                
                self.delta.newOwner = self.player
                                
                        
                
                if ((army == 0 and self.isvisible()) or army > 0 and self.army != army): # Remember Discovered Armies
                        if (self.army == 0 or self.army - army > 1 or self.army - army < -1):
                                armyMovedHere = True
                        oldArmy = self.army
                        self.army = army
                        if (self.delta.oldOwner != self.delta.newOwner):
                                self.delta.armyDelta = 0 - (self.army + oldArmy)
                        else:
                                self.delta.armyDelta = self.army - oldArmy
                        

                if isCity:
                        self.isCity = True
                        self.isGeneral = False
                        if self in map.cities:
                                map.cities.remove(self)
                        map.cities.append(self)
                        
                        playerObj = map.players[self.player]

                        if self in playerObj.cities:
                                playerObj.cities.remove(self)
                        playerObj.cities.append(self)
                        
                        if self in map.generals:
                                map.generals[self._general_index] = None
                elif isGeneral:
                        playerObj = map.players[self.player]
                        playerObj.general = self
                        self.isGeneral = True
                        map.generals[tile] = self
                        self._general_index = self.tile
                return armyMovedHere

def _apply_diff(cache, diff):
        i = 0
        a = 0
        while i < len(diff) - 1:

                # offset and length
                a += diff[i]
                n = diff[i + 1]

                cache[a:a + n] = diff[i + 2:i + 2 + n]
                a += n
                i += n + 2

        if i == len(diff) - 1:
                cache[:] = cache[:a + diff[i]]
                i += 1

        assert i == len(diff)
