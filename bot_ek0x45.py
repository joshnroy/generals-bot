'''
	@ Travis Drake (EklipZ) eklipz.io - tdrake0x45 at gmail)
	April 2017
	Generals.io Automated Client - https://github.com/harrischristiansen/generals-bot
	EklipZ bot - Tries to play generals lol
'''

import logging
import random
from base import bot_base
from base.bot_base import _create_thread
from copy import deepcopy
import time
from collections import deque 
from queue import PriorityQueue

#class A_Node(object):
#	def __init__(self, tile):
#		self.tile = tile
#		self.cost = cost


#def A_search(maze, start, end):
#	expanded = 0 # use to track number of nodes expanded by the algorithm
#	node1 = Node(start,0)
#	frontier = PriorityQueue()
#	frontier.put((dist_to_goal(node1,end) + node1.get_cost(), node1))
#	visited = []
#	in_frontier = [] # keep track of items in frontier, PriorityQueue has no way
#	to peek
#	in_frontier.append(node1)
#	while(True):
#		if(frontier == []):
#			return(None,expanded)
#		curr = (frontier.get())[1]
#		in_frontier.remove(curr)
#		expanded += 1
#		if(curr.get_loc() == end):
#			return(curr,expanded)
#		visited.append(curr.get_loc())
#		neighbors = find_neighbors(maze, curr.get_loc())
#		for neighbor in neighbors:
#			node_n = Node(neighbor,node1.get_cost()+1)
#			node_n.parent = curr
#			if(neighbor not in visited) and (node_n not in in_frontier):
#				frontier.put((dist_to_goal(node_n,end) + node1.get_cost(), node_n))
#				in_frontier.append(node_n)
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

class EklipZBot(object):
	def __init__(self, threadCount):
		self.threadCount = threadCount
		self.threads = []
		self._bot = None
		self._map = None
		self.curPath = None
		self.curPathPrio = -1
		self.gathers = 0
		self.lastSearched = []
		self.searchHistory = []
		self.searchHistory.append([])
		self.searchHistory.append([])
		self.searchHistory.append([])
		self.searchHistory.append([])
		self.searchHistory.append([])
		self.searchHistory.append([])
		self.attacks = 0
		self.leafMoves = []
		self.largeVisibleEnemyTiles = []
		self.attackFailedTurn = 0
		self.countFailedQuickAttacks = 0
		self.countFailedHighDepthAttacks = 0
		self.indanger = False
		self.enemyCities = []
		self.turnsTillDeath = -1
		self.evaluatedGrid = []
		self.largeTilesNearEnemyKings = {}
		self.danger = None
		self.generalApproximations = []
		self.allUndiscovered = []

		self._minAllowableArmy = -1
		
	def spawnWorkerThreads(self):
		return
		
	def dummyMover(self, allowRetry = True):
		start = time.time()
		
		print("\n       ~~~\n       Turn {}\n       ~~~\n".format(self._map.turn))
		self._minAllowableArmy = -1
		self.lastEvaluatedGrid = self.evaluatedGrid
		if (len(self.lastEvaluatedGrid) == 0):
			self.lastEvaluatedGrid = [[0 for x in range(self._map.rows)] for y in range(self._map.cols)]
		self.evaluatedGrid = [[0 for x in range(self._map.rows)] for y in range(self._map.cols)]
		#print('thingy')
		self.indanger = False
		self._map.ekBot = self
		histLen = len(self.searchHistory)
		for i in range(histLen):
			if (i == histLen - 2):
				break
			self.searchHistory[histLen - i - 1] = self.searchHistory[histLen - i - 2]
		self.searchHistory[0] = self.lastSearched
		self.lastSearched = []
		self.enemyCities = []
		
		
		if (self._map.turn < 23):
			return None
		if (self.turnsTillDeath > 0):
			self.turnsTillDeath -= 1
			self.indanger = True
			#print("\n\n---------TURNS TILL DEATH AT MOVE START {}\n".format(self.turnsTillDeath))
		self.scan_map()
		
		allLeaves = self.leafMoves
		#TODO fix prio
		if (self.curPath != None and (self.curPath.tile.army <= 2 or self.curPath.tile.player != self._map.player_index or self.curPath.tile.isGeneral)):
			if (self.curPath.parent != None and self.curPath.parent.parent != None and self.curPath.parent.parent.parent != None and self.curPath.tile == self.curPath.parent.parent.tile and self.curPath.parent.tile == self.curPath.parent.parent.parent.tile):
				print("\n\n\n~~~~~~~~~~~\nDe-duped path\n~~~~~~~~~~~~~\n\n~~~\n")
				self.curPath = self.curPath.parent.parent.parent
			elif (self.curPath.parent != None and self.curPath.tile.x == self.curPath.parent.tile.x and self.curPath.tile.y == self.curPath.parent.tile.y):
				print("           wtf, doubled up tiles in path?????")
				self.curPath = self.curPath.parent.parent
			else:
				self.curPath = self.curPath.parent
		else:
			"         --         missed move?"
		#elif(self.curPath != None):
		#	print("\n!!~~!!~~ OH DAMN LOOKS LIKE WE MISSED A MOVE! ~~!!~~!!")
		#	if (self.curPath.parent != None):
		#		print("!!~~!!~~ [{}: {}] {},{} -> [{}: {}] {},{} ~~!!~~!!\n".format(self.curPath.tile.player, self.curPath.tile.army, self.curPath.tile.x, self.curPath.tile.y, self.curPath.parent.tile.player, self.curPath.parent.tile.army, self.curPath.parent.tile.x, self.curPath.parent.tile.y))
		#	else: 
		#		print("!!~~!!~~ parent was None ~~!!~~!!\n")


		if (self.curPathPrio >= 0):
			print("curPathPrio: " + str(self.curPathPrio))
		self.calculate_general_danger()
		turnsTillDanger = -1 if self.danger == None else self.danger[0]

		for king in self.largeTilesNearEnemyKings.keys():
			tiles = self.largeTilesNearEnemyKings[king]
			if (len(tiles) > 0):
				print("Attempting to find kill path against general {} ({},{})".format(king.player, king.x, king.y))
				(pathEnd, path) = self.a_star_kill(tiles, king, 0.03, 45)
				if (path != None and pathEnd.turn >= 0) and (self.danger == None or not self.danger[3] or turnsTillDanger > pathEnd.turn):
					print("Found kill path :^)")
					self.curPath = path
					self.curPathPrio = 5
					return Move(path.tile, path.parent.tile)

		general = self._map.generals[self._map.player_index]
		paths = []
		if self.curPathPrio > 10:
			self.indanger = True
		genLowArmy = self.general_min_army_allowable() / 2 > general.army
		if (genLowArmy):
			print("gen low army")
		if (genLowArmy) or (turnsTillDanger > -1 and (self.danger[3] or self.curPathPrio < 10) and (self.curPathPrio < 100 or self.turnsTillDeath > turnsTillDanger)):
			armyAmount = self.general_min_army_allowable() - general.army if self.danger == None else self.danger[1] + 1
			self.indanger = True
			searchTurns = turnsTillDanger - 1
			self.turnsTillDeath = turnsTillDanger
			if searchTurns <= 0:
				print("searchTurns <= 0, setting to 7")
				searchTurns = 7
			#if (searchTurns < 2):
			#	searchTurns = 10
			print("\n!-!-!-!-!-!  general in danger in {}, gather {} to general in {} turns  !-!-!-!-!-!".format(turnsTillDanger, armyAmount, searchTurns))
			destinations = []
			destinations.append(general)
			self.lastSearched.append(general)
			gatherPaths = []
			if (self.danger != None and self.danger[3]):
				gatherPaths = self.WeightedBreadthSearch(destinations, max(1, searchTurns), 0.13, general.player, armyAmount, 20)
			else:
				gatherPaths = self.WeightedBreadthSearch(destinations, max(1, searchTurns), 0.13, general.player, -1, 20)
			queue = PriorityQueue()
			for path in gatherPaths:
				if (path[1].value > 0 and path[1].turn > 0):
					print("path to save king, len {}, value {} > 0: {}".format(path[1].turn, path[1].value, stringPath(path[1])))
					queue.put((0 - path[1].value, path))
				else:
					print("IGNORED with low value / length: " + stringPath(path[1]))
			

			while not queue.empty():
				paths.append(queue.get()[1])

			if (len(paths) == 0 and self.danger != None and self.danger[3]):
				print("\n\n!-!-!-!-!-! \nIt may be too late to save general, using longer turncount {} to attempt defense :( \n!-!-!-!-!-!".format(searchTurns + 2))
				paths = self.WeightedBreadthSearch(destinations, searchTurns + 6, 0.14, general.player)
			
			if (len(paths) > 0): 
				if (self.danger != None and self.danger[3]):
					self.curPathPrio = 100
				else:
					self.curPathPrio = 100
				self.curPath = paths[0][1]
				print("set curpath to save general." + stringPath(self.curPath))
			end = time.time()
			print("Time calculating defensive gather to general: {}".format(end - start))

	
		#if not (len(paths) > 0) and (not (self.danger != None and self.danger[3]) and (self.curPath == None or self.curPath.parent == None or self.curPathPrio <= 0)): #and leafMove.source.army > 1):
		if len(paths) == 0 and (self.curPath == None or self.curPath.parent == None): #and leafMove.source.army > 1):
			leafMoves = self.find_greatest_expansion_leaves(allLeaves)
			if (len(leafMoves) > 0):
				#self.curPath = None
				#self.curPathPrio = -1
				move = leafMoves[0]
				i = 0
				valid = True
				while move.source.isGeneral and not self.general_move_safe(move.dest):
					move = random.choice(leafMoves)
					i += 1
					if i > 10:
						print("broke after 10 attempts to find a different leaf move other than unsafe general move.")
						break
				self.curPath = None
				self.curPathPrio = -1
				end = time.time()
				print("Leaf Move duration: {}".format(end - start))
				return move

		if (self.curPath == None or self.curPath.parent == None):
					
			if (general != None):					
				highPriAttack = False
				attackable = []
				if (self.attackFailedTurn <= self._map.turn - 50):
					for gen in self._map.generals:
						if (gen != None and gen.player != self._map.player_index):
							attackable.append(gen)
							#killPath = self.a_star_kill(player, gen, 0.02, 25)
							highPriAttack = True
				#attack undiscovered tiles and cities
				if (self._map.turn > 200 and self._map.turn % 3 == 0 and len(attackable) == 0):
					print("\n------------\nGathering to attack undiscovered or cities {}:\n------------\n".format(len(attackable)))
					prio = PriorityQueue()					
					for tile in self.get_enemy_undiscovered():
						prio.put((0 - self.euclidDist(tile.x, tile.y, self.generalApproximations[tile.player][0], self.generalApproximations[tile.player][1]), tile))
					iter = 0
					while not prio.empty() and iter < 4:
						iter += 1
						attackable.append(prio.get()[1])

					if (len(attackable) == 0 or self._map.turn % 6 == 0):
						for city in self.enemyCities:
							attackable.append(city)					
						for enemyTile in self.largeVisibleEnemyTiles:
							attackable.append(enemyTile)
					if (len(attackable) == 0):
						attackable = self.allUndiscovered
				
				toAttack = random.sample(attackable, min(4, len(attackable)))

				if (len(paths) == 0 and len(toAttack) > 0):
					for attackee in toAttack:
						self.lastSearched.append(attackee)
					self.attacks += 1
					print("\n------------\nGathering to attack {} tiles\n------------\n".format(len(toAttack)))
					paths = self.WeightedBreadthSearch(toAttack, 50, 0.18)
					if (len(paths) == 0 and highPriAttack):
						self.countFailedQuickAttacks += 1
						print("\n------------\nCOULD NOT FIND QUICK ROUTE TO ATTACK TILES {} TIMES, RUNNING LONGER SEARCH\n------------\n".format(self.countFailedQuickAttacks))
						
						paths = self.WeightedBreadthSearch(toAttack, 80, 2.0)
						
						if (len(paths) == 0):
							self.countFailedHighDepthAttacks += 1
							print("\n------------\nCOULD NOT FIND ROUTE TO ATTACK TILES {} TIMES EVEN WITH LONGER SEARCH :(\n------------\n".format(self.countFailedHighDepthAttacks))
							self.attackFailedTurn = self._map.turn
					self.curPathPrio = 8

				if (len(paths) == 0): #if we're not attacking a general. God my code is bad						
					if (len(allLeaves) > 0):
						#gather on leaf
						#TODO pick good leaf targets. Cities? Enemy 1's? Emptier areas of the map?
						print("gather to leaf OR CITIES")
						destinations = []
						destinations.extend(self.enemyCities)
						if (self._map.turn % 11 != 0):
							moves = self.find_target_gather_leaves(allLeaves)
							if (len(moves) == 0):
								print("\n\nNO LEAF MOVES FOUND??????????\n")
							for move in moves:
								destinations.append(move.dest)
						if (len(destinations) > 0):
							targets = random.sample(destinations, min(len(destinations), 3))
							for dest in targets:
								self.lastSearched.append(dest)
							paths = self.WeightedBreadthSearch(targets, 50, 0.18)
							self.curPathPrio = 1
							if (len(paths) == 0):
								for dest in targets:
									print("NO PATHS WERE RETURNED FOR {},{}??????????".format(dest.x, dest.y))
									
				if (len(paths) > 0):
					self.curPath = paths[0][1]
					self.gathers += 1
				else:
					self.curPathPrio = -1
		if (self.curPath != None):
			while ((self.curPath.tile.army <= 1 or self.curPath.tile.player != self._map.player_index) and self.curPath.parent != None):
				if (self.curPath.tile.army <= 1):
					print("!!!!\nMove was from square with 1 or 0 army\n!!!!! {},{} -> {},{}".format(self.curPath.tile.x, self.curPath.tile.y, self.curPath.parent.tile.x, self.curPath.parent.tile.y))
				elif (self.curPath.tile.player != self._map.player_index):
					print("!!!!\nMove was from square OWNED BY THE ENEMY\n!!!!! [{}] {},{} -> {},{}".format(self.curPath.tile.player, self.curPath.tile.x, self.curPath.tile.y, self.curPath.parent.tile.x, self.curPath.parent.tile.y))
				self.curPath = self.curPath.parent
				
			if (self.curPath.parent != None):
				if (self.curPath.tile.isGeneral and not self.general_move_safe(self.curPath.parent.tile)):
					self.curPath = None	
					self.curPathPrio = -1
					print("General move in path would have violated general min army allowable. Repathing.")
				else:
					move = Move(self.curPath.tile, self.curPath.parent.tile)
					end = time.time()
					print("Path Move Duration: {}".format(end - start))
					return move
			self.curPath = None	
		self.curPathPrio = -1
		end = time.time()
		print("!!!!\nFOUND NO MOVES {}\n!!!!!".format(end - start))
		if (allowRetry):
			print("Retrying.")
			return self.dummyMover(False)
		return None
	

	def get_enemy_undiscovered(self):
		enemyUndiscovered = []
		for tile in self.allUndiscovered:			
			for i in [[tile.x - 1,tile.y],[tile.x + 1,tile.y],[tile.x,tile.y - 1],[tile.x,tile.y + 1]]: #new spots to try
				siblingTile = GetTile(self._map, i[0], i[1])
				if (siblingTile != None and siblingTile.player != -1):
					enemyUndiscovered.append(tile)
		return enemyUndiscovered
	
	def shortestPath(self, start, goal):
		return a_star_search(start, goal, _shortestPathHeur, _shortestPathCost)


	def _shortestPathHeur(self, goal, cur):
		return abs(goal.x - cur.x) + abs(goal.y - cur.y)

	def _shortestPathCost(self, a, b):
		return 1

	def euclidDist(self, x, y, x2, y2):
		return pow(pow(abs(x - x2), 2) + pow(abs(y - y2), 2), 0.5)

	#def minimax_defense(self, startTiles, goal, maxTime = 0.1, maxDepth = 20):

	#	frontier = deque()
	#	visited = [[{} for x in range(self._map.rows)] for y in range(self._map.cols)]
	#	for start in startTiles:
	#		frontier.appendleft((start, 0, start.army))
	#		visited[start.x][start.y][0] = (start.army, None)
	#	start = time.time()
	#	iter = 0
	#	foundGoal = False
	#	foundArmy = -1
	#	foundDist = -1
	#	depthEvaluated = 0
	#	while not len(frontier) == 0:
	#		iter += 1
	#		if (iter % 100 == 0 and time.time() - start > maxTime):
	#			break
			
	#		(current, dist, army) = frontier.pop()


	#		x = current.x
	#		y = current.y				
			
	#		if current == goal:
	#			if army > 0 and army > foundArmy:
	#				foundGoal = True
	#				foundDist = dist
	#				foundArmy = army
	#			else: # skip paths that go through king, that wouldn't make sense
	#				continue
	#		if dist > depthEvaluated:
	#			depthEvaluated = dist
	#		if (dist <= maxDepth and not foundGoal):
	#			for i in [[x - 1,y],[x + 1,y],[x,y - 1],[x,y + 1]]: #new spots to try
	#				if (i[0] < 0 or i[1] < 0 or i[0] >= self._map.cols or i[1] >= self._map.rows):
	#					continue
	#				next = self._map.grid[i[1]][i[0]]
	#				inc = 0 if not (next.isCity or next.isGeneral) else dist / 2
	#				self.evaluatedGrid[next.x][next.y] += 1
	#				if (next.mountain or (not next.discovered and next.isobstacle())):
	#					continue
	#				#new_cost = cost_so_far[current] + graph.cost(current, next)
	#				nextArmy = army - 1
	#				if (startTiles[0].player == next.player):
	#					nextArmy += next.army + inc
	#				else:
	#					nextArmy -= (next.army + inc)
	#					if (nextArmy <= 0):
	#						continue
	#				newDist = dist + 1
	
	#				if newDist not in visited[next.x][next.y] or visited[next.x][next.y][newDist][0] < nextArmy:
	#					visited[next.x][next.y][newDist] = (nextArmy, current)
	#				frontier.appendleft((next, newDist, nextArmy))

	#	print("BFS SEARCH ITERATIONS {}, DURATION: {}, DEPTH: {}".format(iter, time.time() - start, depthEvaluated))
	#	if foundDist < 0:
	#		return None
		
	#	pathStart = PathNode(goal, None, foundArmy, foundDist, -1, None)
	#	path = pathStart
	#	node = goal
	#	dist = foundDist
	#	while (node != None):
	#		army, node = visited[node.x][node.y][dist]
	#		dist -= 1
	#		path = PathNode(node, path, army, dist, -1, None) 

	#	print("BFS FOUND KILLPATH OF LENGTH {} VALUE {}".format(pathStart.turn, pathStart.value))
	#	return pathStart


	def breadth_first_kill(self, startTiles, goal, maxTime = 0.1, maxDepth = 20):
		frontier = deque()
		visited = [[{} for x in range(self._map.rows)] for y in range(self._map.cols)]
		for start in startTiles:
			visitedSet = set()
			visitedSet.add((start.x, start.y))
			frontier.appendleft((start, 0, start.army, visitedSet))
			visited[start.x][start.y][0] = (start.army, None)
		start = time.time()
		iter = 0
		foundGoal = False
		foundArmy = -1
		foundDist = -1
		depthEvaluated = 0
		while not len(frontier) == 0:
			iter += 1
			if (iter % 25 == 0 and time.time() - start > maxTime):
				break
			
			(current, dist, army, visitedSet) = frontier.pop()
			

			x = current.x
			y = current.y				
			
			if current == goal:
				if army > 0 and army > foundArmy:
					foundGoal = True
					foundDist = dist
					foundArmy = army
				else: # skip paths that go through king, that wouldn't make sense
					continue
			if dist > depthEvaluated:
				depthEvaluated = dist
			if (dist <= maxDepth and not foundGoal):
				for i in [[x - 1,y],[x + 1,y],[x,y - 1],[x,y + 1]]: #new spots to try
					if (i[0] < 0 or i[1] < 0 or i[0] >= self._map.cols or i[1] >= self._map.rows):
						continue
					nextSetEntry = (i[0], i[1])
					if (nextSetEntry in visitedSet):
						continue
					next = self._map.grid[i[1]][i[0]]
					
					if (next.mountain or (not next.discovered and next.isobstacle())):
						continue
					self.evaluatedGrid[next.x][next.y] += 1
					inc = 0 if not (next.isCity or next.isGeneral) else dist / 2
					#new_cost = cost_so_far[current] + graph.cost(current, next)
					nextArmy = army - 1
					if (startTiles[0].player == next.player):
						nextArmy += next.army + inc
					else:
						nextArmy -= (next.army + inc)
						if (nextArmy <= 0):
							continue
					newDist = dist + 1
					newVisitedSet = set(visitedSet)
					newVisitedSet.add(nextSetEntry)
					if newDist not in visited[next.x][next.y] or visited[next.x][next.y][newDist][0] < nextArmy:
						visited[next.x][next.y][newDist] = (nextArmy, current)
					frontier.appendleft((next, newDist, nextArmy, newVisitedSet))

		print("BFS SEARCH ITERATIONS {}, DURATION: {}, DEPTH: {}".format(iter, time.time() - start, depthEvaluated))
		if foundDist < 0:
			return (None, None)
		
		pathStart = PathNode(goal, None, foundArmy, foundDist, -1, None)
		path = pathStart
		node = goal
		dist = foundDist
		while (node != None):
			army, node = visited[node.x][node.y][dist]
			if (node != None):
				dist -= 1
				path = PathNode(node, path, army, dist, -1, None) 

		print("BFS FOUND KILLPATH OF LENGTH {} VALUE {}\n{}".format(pathStart.turn, pathStart.value, stringPath(path)))
		return (pathStart, path)


	def a_star_kill(self, startTiles, goal, maxTime = 0.1, maxDepth = 20):

			
		frontier = PriorityQueue()
		came_from = {}
		cost_so_far = {}
		for start in startTiles:
			print("a* enqueued start tile {},{}".format(start.x, start.y))
			cost_so_far[start] = (0, 0 - start.army)	
			frontier.put((cost_so_far[start], start))
			came_from[start] = None	
		start = time.time()
		iter = 0
		foundDist = -1
		foundArmy = -1
		foundGoal = False
		depthEvaluated = 0
		while not frontier.empty():
			iter += 1
			if (iter % 25 == 0 and time.time() - start > maxTime):
				print("breaking early")
				break
			prio, current = frontier.get()
			x = current.x
			y = current.y				
			curCost = cost_so_far[current]
			dist = curCost[0]
			army = 0 - curCost[1]
			addUndiscovered = startTiles[0].player != self._map.player_index
						
			if dist > depthEvaluated:
				depthEvaluated = dist
			if current == goal:
				if army > 1 and army > foundArmy:
					foundDist = dist
					foundArmy = army
					foundGoal = True
					print("A* found goal, breaking")
					break
				else: # skip paths that go through king, that wouldn't make sense
					#print("a* path went through king")
					continue
			if (dist < maxDepth):
				for i in [[x - 1,y],[x + 1,y],[x,y - 1],[x,y + 1]]: #new spots to try
					if (i[0] < 0 or i[1] < 0 or i[0] >= self._map.cols or i[1] >= self._map.rows):
						continue
					next = self._map.grid[i[1]][i[0]]
					if (next.mountain or ((not next.discovered) and next.isobstacle())):
						#print("a* mountain")
						continue
					inc = 0 if not (next.isCity or next.isGeneral) else (dist + 1) / 2
					self.evaluatedGrid[next.x][next.y] += 1
					
					#new_cost = cost_so_far[current] + graph.cost(current, next)
					nextArmy = army - 1
					if (startTiles[0].player == next.player or not next.discovered):
						nextArmy += next.army + inc
					else:
						nextArmy -= (next.army + inc)
					if (nextArmy <= 0):
						#print("a* next army <= 0: {}".format(nextArmy))
						continue
					new_cost = (dist + 1, (0 - nextArmy))
					if next not in cost_so_far or new_cost < cost_so_far[next]:
						cost_so_far[next] = new_cost
						priority = (dist + 1 + self._shortestPathHeur(goal, next), 0 - nextArmy)
						frontier.put((priority, next))
						#print("a* enqueued next")
						came_from[next] = current
		print("A* KILL SEARCH ITERATIONS {}, DURATION: {}, DEPTH: {}".format(iter, time.time() - start, depthEvaluated))
		if not goal in came_from:
			return (None, None)
		pathStart = PathNode(goal, None, foundArmy, foundDist, -1, None)
		path = pathStart
		node = goal
		dist = foundDist
		while (came_from[node] != None):
			#print("Node {},{}".format(node.x, node.y))
			node = came_from[node]
			dist -= 1
			path = PathNode(node, path, foundArmy, dist, -1, None) 
		print("A* FOUND KILLPATH OF LENGTH {} VALUE {}\n{}".format(pathStart.turn, pathStart.value, stringPath(path)))
		return (pathStart, path)




	def a_star_search(self, start, goal, heurFunc, costFunc, goalFunc):
		frontier = PriorityQueue()
		frontier.put(start, 0)
		came_from = {}
		cost_so_far = {}
		came_from[start] = None
		cost_so_far[start] = 0
    
		while not frontier.empty():
			current = frontier.get()
			x = current.x
			y = current.y
			if current == goal:
				break
			for i in [[x - 1,y],[x + 1,y],[x,y - 1],[x,y + 1]]: #new spots to try
				if (i[0] < 0 or i[1] < 0 or i[0] >= self._map.cols or i[1] >= self._map.rows):
					continue
				next = self._map.grid[i[1]][i[0]]
				if (next.mountain or (not next.discovered and next.isobstacle())):
					continue
				#new_cost = cost_so_far[current] + graph.cost(current, next)
				new_cost = cost_so_far[current] + costFunc(self, current, next)
				if next not in cost_so_far or new_cost < cost_so_far[next]:
					cost_so_far[next] = new_cost
					priority = new_cost + heurFunc(self, goal, next)
					frontier.put(priority, next)
					came_from[next] = current
    
		return came_from, cost_so_far







	#def a_star_search(self, start, goal, includeArmyCost = False):
	#	frontier = PriorityQueue()
	#	frontier.put(start, 0)
	#	came_from = {}
	#	cost_so_far = {}
	#	came_from[start] = None
	#	cost_so_far[start] = 0
    
	#	while not frontier.empty():
	#		current = frontier.get()
	#		x = current.x
	#		y = current.y
	#		if current == goal:
	#			break
	#		for i in [[x - 1,y],[x + 1,y],[x,y - 1],[x,y + 1]]: #new spots to try
	#			if (i[0] < 0 or i[1] < 0 or i[0] >= self._map.cols or i[1] >= self._map.rows):
	#				continue
	#			next = self._map.grid[i[1]][i[0]]

	#			new_cost = cost_so_far[current] + graph.cost(current, next)
	#			if next not in cost_so_far or new_cost < cost_so_far[next]:
	#				cost_so_far[next] = new_cost
	#				priority = new_cost + shortestPathHeur(goal, next)
	#				frontier.put(priority, next)
	#				came_from[next] = current
    
	#	return came_from, cost_so_far


	def WeightedBreadthSearch(self, tiles, maxLength=50, maxTime = 0.2, playerSearching = -2, armyAmount = -1, returnAmount = 10, maximizeTurns = False): 
		loggingOn = False
		frontier = PriorityQueue()
		tileArr = tiles
		tiles = set()
		for tile in tileArr:
			tiles.add(tile)
		Map = self._map
		#print("searching, len tiles {}".format(len(tiles)))
		if (playerSearching == -2):
			playerSearching = Map.player_index
		general = Map.generals[playerSearching]
		generalPlayer = Map.players[playerSearching]
		cityRatio = self.get_city_ratio(playerSearching)


		for tile in tiles:
			if (tile.player == playerSearching):
				if (armyAmount != -1):
					print("\n\n------\nSearching nonstandard army amount {} to {},{}\n--------".format(armyAmount, tile.x, tile.y))
				frontier.put((-10000, PathNode(tile, None, tile.army, 1, 1 if tile.isCity or tile.isGeneral else 0, {(tile.x, tile.y) : 1}), armyAmount, False, 0))
			else:
				isIncrementing = (tile.isCity and tile.player != -1) or tile.isGeneral
				if (isIncrementing):
					print("City or General is in this searches targets: {},{}".format(tile.x, tile.y))
				frontier.put((-10000 * (1 if not tile.isCity else cityRatio), PathNode(tile, None, 0 - tile.army, 1, 1 if tile.isCity or tile.isGeneral else 0, {(tile.x, tile.y) : 1}), 2, isIncrementing, 1))
		leafNodes = PriorityQueue()
		start = time.time()
	

		iter = 1
		undiscoveredTileSearchCount = 0
		score = Map.scores[playerSearching]
		while not frontier.empty(): #make sure there are nodes to check left
		
			if (iter % 20 == 0 and time.time() - start > maxTime):
				break
			
			prioNode = frontier.get() #grab the first node
			prioValue = prioNode[0]
			node = prioNode[1]
			enemyTileCount = prioNode[4]
			x = node.tile.x
			y = node.tile.y
			turn = node.turn
			curTile = node.tile

			#Map[x][y]="explored" #make this spot explored so we don't try again
		
			if (turn <= maxLength):
				value = node.value
				cityCount = node.cityCount
				pathDict = node.pathDict
				#if (loggingOn):
				#	print("{} evaluating {},{}: turn {} army {}".format(prioNode[0], x, y, turn, value))

				targetArmy = prioNode[2]
				isIncrementing = prioNode[3]
		
				neededArmy = targetArmy + 2
				if (isIncrementing):
					neededArmy += (turn / 2)
		
				for i in [[x - 1,y],[x + 1,y],[x,y - 1],[x,y + 1]]: #new spots to try
					containsCount = pathDict.get((i[0], i[1]), 0)
					if (containsCount <= 1):
						candTile = GetTile(Map, i[0], i[1])
						if (candTile != None and not (candTile.mountain)): 
							#if (candTile in tiles):
							#	print("Skipped tile because it is already the paths target.")
							#	continue
							self.evaluatedGrid[candTile.x][candTile.y] += 1
							candTileArmyVal = 0
							dangerousGeneralMove = False
							
							# if we've already visited this tile
							if (containsCount >= 1):
								#if (loggingOn):
								#	print("revisiting path {},{}".format(candTile.x, candTile.y))
								candTileArmyVal = value - 1
						
							# if this tile is owned by the current player
							elif candTile.player == playerSearching:
								candTileArmyVal = value + (candTile.army - 1)
								if (candTile.isGeneral and Map.turn > 100):
									if playerSearching == Map.player_index:
										if (not self.general_move_safe(candTile)):
											print("Bot is in danger. Refusing to use general tile altogether.")
											continue
										candTileArmyVal -= candTile.army / 2
											
							
							# if this is an undiscovered neutral tile
							elif not candTile.discovered: 
								if (candTile.isobstacle()):
									candTileArmyVal = value - 50
								else:
									candTileArmyVal = value - (candTile.army + 1)
								undiscoveredTileSearchCount += 1
							else: 
								candTileArmyVal = value - (candTile.army + 1)
							weightedCandTileArmyVal = candTileArmyVal
							if (targetArmy > 0 and candTileArmyVal > neededArmy):
								#weightedCandTileArmyVal = 2 * (candTileArmyVal - neededArmy) / 3 + neededArmy
								weightedCandTileArmyVal = pow(candTileArmyVal - neededArmy, 0.9) + neededArmy
							#paths starting through enemy territory carry a zero weight until troops are found, causing this to degenerate into breadth first search until we start collecting army (due to subtracting turn)
							#weight paths closer to king
							if (weightedCandTileArmyVal <= 0 and general != None):
								distToGen = dist(candTile, general)
								weightedCandTileArmyVal = weightedCandTileArmyVal - distToGen 
								#if (loggingOn):
								#	print("{},{} weightedCandTileArmyVal <= 0, weighted: {}".format(candTile.x, candTile.y, weightedCandTileArmyVal))
							#elif(loggingOn):
							#	print("{},{} weightedCandTileArmyVal > 0, weighted: {}".format(candTile.x, candTile.y, weightedCandTileArmyVal))
															
							if (dangerousGeneralMove):
								weightedCandTileArmyVal = weightedCandTileArmyVal / 2
							candTileCityCount = cityCount if containsCount > 0 or not (candTile.isCity and candTile.player != -1) else cityCount + 1
							candPathDict = pathDict.copy()
							candPathDict[(candTile.x, candTile.y)] = containsCount + 1
							candTileEnemyTileCount = enemyTileCount	
							if (candTile.player != self._map.player_index and candTile.player != -1) or not candTile.discovered:
								candTileEnemyTileCount += 1
								if (candTile.isCity and containsCount == 0):
									candTileEnemyTileCount += (9 * cityRatio)
							tileWeight = 0
							#if (maximizeTurns):
							#	weightedCandTileArmyVal - turn - score['total'] / 750.0 * pow(turn, 1.5)
							#else:
							tileWeight = candTileEnemyTileCount + (candTileEnemyTileCount / 4.0 + candTileCityCount * 2) * weightedCandTileArmyVal + 14 * weightedCandTileArmyVal / turn - turn - (score['total'] / 900.0) * pow(turn, 1.33)
								#tileWeight = (candTileCityCount + 2) * weightedCandTileArmyVal + 13 * weightedCandTileArmyVal / turn - turn - score['total'] / 750.0 * pow(turn, 1.5)
							#if (loggingOn): print("{},{} fullWeight: {}".format(candTile.x, candTile.y, tileWeight))
							frontier.put((0 - tileWeight, PathNode(candTile, node, candTileArmyVal, turn + 1, candTileCityCount, candPathDict), targetArmy, isIncrementing, candTileEnemyTileCount))#create the new spot, with node as the parent
					#elif(loggingOn):
					#	print("{},{} already showed up twice".format(x, y))
			if (curTile.player == playerSearching and curTile.army > 1 and targetArmy < value):
				leafNodes.put(prioNode)
			iter += 1
		best = []
		for i in range(returnAmount):
			if (leafNodes.empty()):
				break
			node = leafNodes.get()
			best.append(node)
		
		if (len(best) > 0):
			print("best: " + str(best[0][0]) + "\n" + stringPath(best[0][1]))
		end = time.time()
		print("SEARCH ITERATIONS {}, DURATION: {}".format(iter, end - start))
		#if (undiscoveredTileSearchCount > 0):
		#	print("~~evaluated undiscovered tiles during search: " + str(undiscoveredTileSearchCount))
		return best


	def get_city_ratio(self, player_index):
		enemyCityMax = 0
		generalPlayer = self._map.players[player_index]
		for player in self._map.players:
			if player.index != player_index and not player.dead:
				enemyCityMax = max(player.cityCount, enemyCityMax)
		cityRatio = 1.0 * enemyCityMax / generalPlayer.cityCount
		return cityRatio

	def evaluate_optimal_attack_paths(self, sourceTile):
		friendlyWaypoints = list(_map.players[sourceTile.player].cities)
	
	
	

	def calculate_general_danger(self):
		self.danger = None
		general = self._map.generals[self._map.player_index]
		if (general == None):
			return 
		otherPlayers = []
		otherScores = []
		minDanger = 1000
		
		self.numPlayers = 1
		generalScore = self._map.scores[self._map.player_index]

		
		realDanger = False
		dangerousPath = None
		dangerValue = 1000
		minAllowable = self.general_min_army_allowable()
		if (general.army < minAllowable):
			dangerValue = minAllowable - general.army
			minDanger = 25
		playerTiles = [[] for i in range(8)]
		for tile in self.largeVisibleEnemyTiles:
			#print("    Large enemy tile: {},{}: {}".format(tile.x, tile.y, tile.army))
			self.lastSearched.append(tile)
			playerTiles[tile.player].append(tile)
		minRealDanger = 1000
		for player in playerTiles:
			if (len(player) > 0):
				killPath = None
				killPathEnd = None
				for tile in player:	
					(potKillPathEnd, potKillPath) = self.a_star_kill(player, general, 0.02, 30)
					if (potKillPath != None and (killPath == None or potKillPathEnd.turn < killPathEnd.turn)):
						killPath = potKillPath		
						killPathEnd = potKillPathEnd
				if (killPath != None and killPathEnd.turn < minRealDanger):
					#self.lastSearched.append(path[1].tile)
					print("A*  Kill path against our general:\n{}".format(stringPath(killPath)))
					dangerousPath = killPath
					dangerValue = killPathEnd.value
					minRealDanger = killPathEnd.turn
					realDanger = True
				else: #attempt BFS
					closeTiles = []
					for tile in player:
						if dist(tile, general) < 10:
							closeTiles.append(tile)
					if len(closeTiles) > 0:
						(killPathBreadthEnd, killPathBreadth) = self.breadth_first_kill(closeTiles, general, 0.04, 10)
						if (killPathBreadth != None and killPathBreadthEnd.turn < minRealDanger):
							print("BFS Kill path against our general:\n{}".format(stringPath(killPathBreadth)))
							#self.lastSearched.append(path[1].tile)
							dangerousPath = killPathBreadth
							dangerValue = killPathBreadthEnd.value
							minRealDanger = killPathBreadthEnd.turn
							realDanger = True
		minDanger = min(minDanger, minRealDanger)

		if (minDanger == 1000):
			minDanger = -1
		if (minDanger != -1):
			print("    Evaluated if general is in danger from {} players: {} turns to death by value {}".format(len(otherPlayers), minDanger, dangerValue))
			self.danger = (minDanger, dangerValue, dangerousPath, realDanger)
			


	def general_min_army_allowable(self):
		if (self._minAllowableArmy != -1):
			return self._minAllowableArmy
		general = self._map.generals[self._map.player_index]
		if (general == None):
			return -1
		maxPlayerPotentialArmy = 0
		generalScore = self._map.scores[self._map.player_index]
		generalPlayer = self._map.players[self._map.player_index]
		
		realDanger = False
		dangerousPath = None
		dangerValue = -1
		if self._map.remainingPlayers <= 3 and self._map.turn > 100:
			for player in self._map.players:
				if player == generalPlayer or player == None:
					continue
				# when we have 30% income lead and 5% army disadvantage or better
				if (10.0 * (generalPlayer.tileCount + 25*generalPlayer.cityCount) / max(1, player.tileCount + 25*player.cityCount) > 13 and 10.0 * generalPlayer.standingArmy / max(1, player.standingArmy) > 9):
					if (player.knowsKingLocation):
						potentialArmy = player.standingArmy / 2 
					else:
						potentialArmy = player.standingArmy / 4 
					if (maxPlayerPotentialArmy < potentialArmy):
						maxPlayerPotentialArmy = potentialArmy
						
		minAllowableArmy = maxPlayerPotentialArmy

		self._minAllowableArmy = minAllowableArmy
		return minAllowableArmy

	

	def general_move_safe(self, target):
		general = self._map.generals[self._map.player_index]
		minArmy = self.general_min_army_allowable()
		genArmyAfterMove = general.army / 2 
		if (genArmyAfterMove <= minArmy):
			return False
		if (self._map.turn <= 100):
			genArmyAfterMove = 1
		dangerTiles = set()
		for i in range(general.x - 2, general.x + 3):
			for j in range(general.y - 2, general.y + 3):
				tile = GetTile(self._map, i, j)
				if (tile != None and tile.player != general.player and tile.player != -1 and tile.army - 1 > genArmyAfterMove):					
					dangerTiles.add(tile)
		#print("~\n~\nGenArmyAfterMove {}, len(dangerTiles) {}, target {},{}.".format(genArmyAfterMove, len(dangerTiles), target.x, target.y))
		
		
		safeSoFar = True
		if (len(dangerTiles) > 1):
			safeSoFar = False
		for dangerTile in dangerTiles:
			if not (target.x  == dangerTile.x and target.y == dangerTile.y):
				safeSoFar = False
				print("Enemy tile at {},{} with value {} is preventing king moves.".format(dangerTile.x, dangerTile.y, dangerTile.army))
			else:
				print("\n~~~Allowed otherwise-illegal king move to attack the dangerous tile at {},{} with value {}.".format(dangerTile.x, dangerTile.y, dangerTile.army))
		return safeSoFar
			
					

	def find_target_gather_leaves(self, allLeaves=None):
		general = self._map.generals[self._map.player_index]
		mapMid = (self._map.cols / 2, self._map.rows / 2)
		maxMoves = PriorityQueue()
		player = self._map.players[self._map.player_index]
		cityRatio = self.get_city_ratio(self._map.player_index)
		for leaf in allLeaves:
			#if (len(maxMoves) == 0 or leaf.source.army - leaf.dest.army >= maxMoves[0].source.army - maxMoves[0].dest.army):
			leafValue = leaf.dest.army

			midWeight = pow(pow(abs(leaf.dest.x - mapMid[0]), 2) + pow(abs(leaf.dest.y - mapMid[1]), 2), 0.5) - (self._map.cols + self._map.rows) / 6
			if (midWeight < 0):
				midWeight = 0
			
			leafValue -= midWeight * 4

			if (leaf.dest.isCity and leaf.dest.player == -1 and (self._map.turn < 125 or self.indanger)):
				continue

			if (leaf.dest.player != -1):
				leafValue = leafValue	
				distToGen = self.euclidDist(leaf.dest.x, leaf.dest.y, general.x, general.y)
				leafValue = leafValue * distToGen
			if (leaf.dest.player != -1 or leaf.dest.isCity):
				leafValue = leafValue + player.standingArmy * 5 / max(2, dist(leaf.dest, general))			
		    
			if (leaf.dest.player != -1):
				leafValue *= 1.5
			if (leaf.dest.isCity):
				distToGen = self.euclidDist(leaf.dest.x, leaf.dest.y, general.x, general.y)
				distToEnemy = self.getDistToEnemy(leaf.dest)
				if (distToEnemy > 0):
					leafValue = leafValue + 30 * (distToEnemy / distToGen) * cityRatio
				else:
					leafValue = leafValue + 40 * cityRatio - distToGen
				#leafValue *= 2.0
			leafValue = 0 - leafValue
			maxMoves.put((leafValue, leaf))
			
		moves = []
		addedSet = set()
		if (not maxMoves.empty()):
			moveNode = maxMoves.get()
			maxMove = moveNode[0]
			leeway = maxMove * 0.95
			#always return at least 5 potential targets
			# less than because the heuristic value goes negative for good values
			while moveNode[0] < leeway or len(moves) < 4:
				moveTuple = (moveNode[1].dest.x, moveNode[1].dest.y)
				if not moveTuple in addedSet:
					addedSet.add(moveTuple)
					moves.append(moveNode[1])
				if (maxMoves.empty()):
					break
				moveNode = maxMoves.get()
		return moves


				 
		
	
	def find_greatest_expansion_leaves(self, allLeaves=None):

		general = self._map.generals[self._map.player_index]
		mapMid = (self._map.cols / 2, self._map.rows / 2)
		maxMoves = []
		for leaf in allLeaves:
			#if (len(maxMoves) == 0 or leaf.source.army - leaf.dest.army >= maxMoves[0].source.army - maxMoves[0].dest.army):
			if (leaf.source.army - leaf.dest.army > 1):
				leafValue = leaf.source.army - leaf.dest.army 
				midWeight = pow(pow(abs(leaf.dest.x - mapMid[0]), 2) + pow(abs(leaf.dest.y - mapMid[1]), 2), 0.5) - (self._map.cols + self._map.rows) / 6
				if (midWeight < 0):
					midWeight = 0
			
				if (leaf.source.isGeneral and not self.general_move_safe(leaf.dest)):
					continue
				if (self.indanger and leaf.dest.player == -1):
					continue
				if (leaf.dest.player != -1):
					leafValue = leafValue * 4
					if (leaf.dest.isGeneral):
						leafValue = 1000000000
					if (leaf.dest.isCity and leaf.dest.player != -1):
						leafValue *= 4
					#if (self._map.turn > 100):
					#	leafValue += (abs(leaf.dest.x - general.x) + abs(leaf.dest.y - general.y)) / 5
				if (len(maxMoves) > 0 and maxMoves[0][0] < leafValue):
					maxMoves = []
				if (len(maxMoves) == 0 or maxMoves[0][0] == leafValue):
					maxMoves.append((leafValue, leaf))
		moves = []
		for moveTuple in maxMoves:
			moves.append(moveTuple[1])
		return moves

	def getDistToEnemy(self, tile):
		dist = 1000
		for i in range(len(self._map.generals)):
			gen = self._map.generals[i]
			genDist = 0
			if (gen != None):
				genDist = self.euclidDist(gen.x, gen.y, tile.x, tile.y)
			elif self.generalApproximations[i][2] > 0:
				genDist = self.euclidDist(self.generalApproximations[i][0], self.generalApproximations[i][1], tile.x, tile.y)
			
			if (genDist < dist):
				dist = genDist
		return dist

	def scan_map(self):
		self.leafMoves = []
		self.largeVisibleEnemyTiles = []
		self.largeTilesNearEnemyKings = {}
		self.allUndiscovered = []
		general = self._map.generals[self._map.player_index]
		generalApproximations = [[0, 0, 0] for i in range(len(self._map.generals))]
		for x in range(general.x - 1, general.x + 2):
			for y in range(general.y - 1, general.y + 2):
				if x == general.x and y == general.y:
					continue
				tile = GetTile(self._map, x, y)
				if tile != None and tile.player != general.player and tile.player != -1:
					self._map.players[tile.player].knowsKingLocation = True
					

		for enemyGen in self._map.generals:
			if (enemyGen != None and enemyGen.player != self._map.player_index):
				self.largeTilesNearEnemyKings[enemyGen] = []
		for x in range(_map.cols):
			for y in range(_map.rows):
				tile = _map.grid[y][x]
				if (not tile.discovered and not tile.isobstacle()):
					self.allUndiscovered.append(tile)
				if (tile.player == _map.player_index):
					for i in [[x - 1,y],[x + 1,y],[x,y - 1],[x,y + 1]]:
						nextTile = GetTile(_map, i[0], i[1])
						if nextTile != None and nextTile.player != _map.player_index and not nextTile.mountain:
							self.leafMoves.append(Move(tile, nextTile))
				elif(tile.player != -1):
					if (self._map.generals[tile.player] == None):
						approx = generalApproximations[tile.player]
						approx[0] += tile.x
						approx[1] += tile.y
						approx[2] += 1
					if(tile.army > max(6, general.army / 2) and tile.isvisible() and not tile.isGeneral):
						self.largeVisibleEnemyTiles.append(tile)
					if(tile.isCity):
						self.enemyCities.append(tile)	
				if (not tile.isvisible() and not (tile.isCity or tile.isGeneral) and (self._map.turn - tile.lastSeen >= 100 or (self._map.turn - tile.lastSeen > 25 and tile.army > 25))):
					tile.army = int(self._map.turn / 250 + 1)
				if tile.player == self._map.player_index and tile.army > 10:
					for enemyGen in self.largeTilesNearEnemyKings.keys():
						if tile.army > enemyGen.army + 1 and dist(tile, enemyGen) < 22:
							self.largeTilesNearEnemyKings[enemyGen].append(tile)
						
		for generalApprox in generalApproximations:
			if (generalApprox[2] > 0):
				generalApprox[0] = generalApprox[0] / generalApprox[2]
				generalApprox[1] = generalApprox[1] / generalApprox[2]
		for i in range(len(self._map.generals)):
			if self._map.generals[i] != None:
				gen = self._map.generals[i]
				generalApproximations[i][0] = gen.x
				generalApproximations[i][1] = gen.y
		self.generalApproximations = generalApproximations	

		


_eklipzBot = EklipZBot(THREAD_COUNT)

def make_move(currentBot, currentMap):
	global _bot, _map
	_bot = currentBot
	_map = currentMap
	_eklipzBot._bot = _bot
	_eklipzBot._map = _map
	
	command = currentBot.getLastCommand()	
	if (command == "-s"):
		return
	
	move = _eklipzBot.dummyMover()
	if (move != None):
		if not place_move(move.source, move.dest):
			print("!!!!!!!!! {},{} -> {},{} was an illegal / bad move!!!!".format(move.source.x, move.source.y, move.dest.x, move.dest.y))
			_eklipzBot.curPath = None
			_eklipzBot.curPathPrio = -1
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
	startup.startup(make_move, "[UW]EklipZ")
	#startup.startup(make_move, "EklipZTest2")
