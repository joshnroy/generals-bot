'''
	@ Harris Christiansen (Harris@HarrisChristiansen.com)
	January 2016
	Generals.io Automated Client - https://github.com/harrischristiansen/generals-bot
	Game Viewer
'''
import os
import pygame
import threading
import time
from copy import deepcopy
from base.client.generals import _spawn

# Color Definitions
BLACK = (0,0,0)
GRAY_DARK = (80,80,80)
GRAY = (160,160,160)
WHITE = (255,255,255)
RED = (200,40,40)
PLAYER_COLORS = [(230,30,30), (30,30,230), (30,128,30), (128,30,128), (30,128,128), (30,90,30), (128,20,20), (230,165,20), (50,230,50)]
FOG_COLOR_OFFSET = 80
KING_COLOR_OFFSET = 45

UP_ARROW = "^"
DOWN_ARROW = "v"
LEFT_ARROW = "<"
RIGHT_ARROW = ">"

# Table Properies
CELL_WIDTH = 35
CELL_HEIGHT = 35
CELL_MARGIN = 1
SCORES_ROW_HEIGHT = 35
INFO_ROW_HEIGHT = 35
PLUS_DEPTH = 8




class GeneralsViewer(object):
	def __init__(self, name=None):
		self._name = name
		self._receivedUpdate = False
		self._readyRender = False
		self.Arrow = None
		

	def updateGrid(self, update):
		updateDir = dir(update)
		self._map = update
		if "bottomText" in updateDir:
			self._bottomText = update.bottomText
		self._scores = sorted(update.scores, key=lambda general: general['total'], reverse=True) # Sort Scores
		
		self._receivedUpdate = True

		if "collect_path" in updateDir:
			self._collect_path = [(path.x, path.y) for path in update.collect_path]
		else:
			self._collect_path = None

	def _initViewier(self):
		pygame.init()

		# Set Window Size
		window_height = self._map.rows * (CELL_HEIGHT + CELL_MARGIN) + CELL_MARGIN + SCORES_ROW_HEIGHT + INFO_ROW_HEIGHT
		window_width = self._map.cols * (CELL_WIDTH + CELL_MARGIN) + CELL_MARGIN
		self._window_size = [window_width, window_height]
		self._screen = pygame.display.set_mode(self._window_size)
		self._transparent = pygame.Surface(self._window_size, pygame.SRCALPHA)

		window_title = "Generals IO Bot"
		if (self._name != None):
			window_title += " - " + str(self._name)
		pygame.display.set_caption(window_title)
		self._font = pygame.font.SysFont('Arial', int(CELL_HEIGHT / 2) - 1)
		self._fontSmall = pygame.font.SysFont('Arial', int(CELL_HEIGHT / 3))
		self._fontLrg = pygame.font.SysFont('Arial', CELL_HEIGHT - 2) 
		self._bottomText = ""

		self._clock = pygame.time.Clock()
		
		self.pathAlphas = []
		self.Arrow = [(CELL_WIDTH / 2, 0), (CELL_WIDTH / 8, CELL_HEIGHT / 2), (CELL_WIDTH / 2, CELL_HEIGHT / 4), (7 * CELL_WIDTH / 8, CELL_HEIGHT / 2)]
		self.repId = self._map.replay_url.split("/").pop()
		self.logDirectory = "H:\\GeneralsLogs\\{}".format(self.repId)
		if not os.path.exists(self.logDirectory):
			os.makedirs(self.logDirectory)
		_spawn(self.save_image)
	def mainViewerLoop(self):
		while not self._receivedUpdate: # Wait for first update
			time.sleep(0.1)

		self._initViewier()

		done = False
		while not done:
			if (self._receivedUpdate):
				self._drawGrid()
				self._receivedUpdate = False
				self._readyRender = True
			for event in pygame.event.get(): # User did something
				if event.type == pygame.QUIT: # User clicked quit
					done = True # Flag done
				elif event.type == pygame.MOUSEBUTTONDOWN: # Mouse Click
					pos = pygame.mouse.get_pos()
					
					# Convert screen to grid coordinates
					column = pos[0] // (CELL_WIDTH + CELL_MARGIN)
					row = pos[1] // (CELL_HEIGHT + CELL_MARGIN)
					
					print("Click ", pos, "Grid coordinates: ", row, column)


			time.sleep(0.1)
		time.sleep(2.0)
		pygame.quit() # Done.  Quit pygame.

	def _drawGrid(self):
		try:


			self._screen.fill(BLACK) # Set BG Color
			self._transparent.fill((0,0,0,0)) # transparent
		
			# Draw Bottom Info Text
			self._screen.blit(self._fontLrg.render("Turn: %d, %s" % (self._map.turn, self._bottomText), True, WHITE), (10, self._window_size[1] - INFO_ROW_HEIGHT))
		
			# Draw Scores
			pos_top = self._window_size[1] - INFO_ROW_HEIGHT - SCORES_ROW_HEIGHT
			score_width = self._window_size[0] / len(self._map.players)
			      #self._scores = sorted(update.scores, key=lambda general: general['total'], reverse=True)
			if (self._map != None):				
				playersByScore = sorted(self._map.players, key=lambda player: player.score, reverse=True) # Sort Scores
				
				for i, player in enumerate(playersByScore):
					if player != None:
						score_color = PLAYER_COLORS[player.index]
						if (player.dead):
							score_color = GRAY_DARK
						pygame.draw.rect(self._screen, score_color, [score_width * i, pos_top, score_width, SCORES_ROW_HEIGHT])
						userString = self._map.usernames[player.index]
						userString = "{} ({})".format(userString, player.stars)
				
						self._screen.blit(self._font.render(userString, True, WHITE), (score_width * i + 3, pos_top + 1))
						self._screen.blit(self._font.render("{} on {} ({})".format(player.score, player.tileCount, player.cityCount), True, WHITE), (score_width * i + 3, pos_top + 1 + self._font.get_height()))
			#for i, score in enumerate(self._scores):
			#	score_color = PLAYER_COLORS[int(score['i'])]
			#	if (score['dead'] == True):
			#		score_color = GRAY_DARK
			#	pygame.draw.rect(self._screen, score_color, [score_width * i, pos_top, score_width, SCORES_ROW_HEIGHT])
			#	userString = self._map.usernames[int(score['i'])]
			#	if (self._map.stars): 
			#		userString = userString + " (" + str(self._map.stars[int(score['i'])]) + ")"
			#	self._screen.blit(self._font.render(userString, True, WHITE), (score_width * i + 3, pos_top + 1))
			#	self._screen.blit(self._font.render(str(score['total']) + " on " + str(score['tiles']), True, WHITE), (score_width * i + 3, pos_top + 1 + self._font.get_height()))
		
			# Draw Grid
			#print("drawing grid")
			for row in range(self._map.rows):
				for column in range(self._map.cols):
					tile = self._map.grid[row][column]
					# Determine BG Color
					color = WHITE
					color_font = WHITE
					if tile.ismountain(): # Mountain
						color = BLACK
					elif tile.player >= 0:
						playercolor = PLAYER_COLORS[tile.player]
						colorR = playercolor[0]
						colorG = playercolor[1]
						colorB = playercolor[2]				
						if (tile.isCity or tile.isGeneral):
							colorR = colorR + KING_COLOR_OFFSET if colorR <= 255 - KING_COLOR_OFFSET else 255
							colorG = colorG + KING_COLOR_OFFSET if colorG <= 255 - KING_COLOR_OFFSET else 255
							colorB = colorB + KING_COLOR_OFFSET if colorB <= 255 - KING_COLOR_OFFSET else 255
						if (not tile.isvisible()): 
							colorR = colorR / 2 + 40
							colorG = colorG / 2 + 40
							colorB = colorB / 2 + 40
						color = (colorR, colorG, colorB)
					elif tile.isobstacle(): # Obstacle
						color = GRAY_DARK
					elif not tile.isvisible(): 
						color = GRAY
					else:
						color_font = BLACK

					pos_left = (CELL_MARGIN + CELL_WIDTH) * column + CELL_MARGIN
					pos_top = (CELL_MARGIN + CELL_HEIGHT) * row + CELL_MARGIN
					if (tile in self._map.generals): # General
						# Draw Plus
						pygame.draw.rect(self._screen, color, [pos_left + PLUS_DEPTH, pos_top, CELL_WIDTH - PLUS_DEPTH * 2, CELL_HEIGHT])
						pygame.draw.rect(self._screen, color, [pos_left, pos_top + PLUS_DEPTH, CELL_WIDTH, CELL_HEIGHT - PLUS_DEPTH * 2])
					elif (tile.isCity): # City
						# Draw Circle
						pos_left_circle = int(pos_left + (CELL_WIDTH / 2))
						pos_top_circle = int(pos_top + (CELL_HEIGHT / 2))
						pygame.draw.circle(self._screen, color, [pos_left_circle, pos_top_circle], int(CELL_WIDTH / 2))
					else:
						# Draw Rect
						pygame.draw.rect(self._screen, color, [pos_left, pos_top, CELL_WIDTH, CELL_HEIGHT])
		
			# Draw path
			#print("drawing path")
			path = self._map.ekBot.curPath
			alpha = 255
			alphaDec = 8
			alphaMin = 145
			while (path != None and path.parent != None):
				s = pygame.Surface((CELL_WIDTH, CELL_HEIGHT))
				# first, "erase" the surface by filling it with a color and
				# setting this color as colorkey, so the surface is empty
				s.fill(WHITE)
				s.set_colorkey(WHITE)
			
				# after drawing the circle, we can set the 
				# alpha value (transparency) of the surface
				tile = path.tile
				toTile = path.parent.tile			
				#print("drawing path {},{} -> {},{}".format(tile.x, tile.y, toTile.x, toTile.y))
				pos_left = (CELL_MARGIN + CELL_WIDTH) * tile.x + CELL_MARGIN
				pos_top = (CELL_MARGIN + CELL_HEIGHT) * tile.y + CELL_MARGIN
				xOffs = 0
				yOffs = 0
				pygame.draw.polygon(s, BLACK, self.Arrow)
				if (tile.x - toTile.x > 0): #left
					#print("left " + str(tile.x) + "," + str(tile.y))
					s = pygame.transform.rotate(s, 90)
					xOffs = -0.3
				elif (tile.x - toTile.x < 0): #right
					#print("right " + str(tile.x) + "," + str(tile.y))
					s = pygame.transform.rotate(s, 270)
					xOffs = 0.3		
				elif (tile.y - toTile.y > 0): #up
					#print("up " + str(tile.x) + "," + str(tile.y))
					yOffs = -0.3
				elif (tile.y - toTile.y < 0): #down
					#print("down " + str(tile.x) + "," + str(tile.y))
					s = pygame.transform.flip(s, False, True)
					yOffs = 0.3

			
				s.set_alpha(alpha)
				self._screen.blit(s, (pos_left + xOffs * CELL_WIDTH, pos_top + yOffs * CELL_HEIGHT))
				path = path.parent	
				alpha -= alphaDec					
				if (alpha < alphaMin):
					alpha = alphaMin			
			
			if (self._map.ekBot.danger != None):
				# Draw danger path
				#print("drawing path")
				path = self._map.ekBot.danger[2]
				alpha = 255
				alphaDec = 8
				alphaMin = 145
				while (path != None and path.parent != None):
					s = pygame.Surface((CELL_WIDTH, CELL_HEIGHT))
					# first, "erase" the surface by filling it with a color and
					# setting this color as colorkey, so the surface is empty
					s.fill(WHITE)
					s.set_colorkey(WHITE)
			
					# after drawing the circle, we can set the 
					# alpha value (transparency) of the surface
					tile = path.tile
					toTile = path.parent.tile			
					#print("drawing path {},{} -> {},{}".format(tile.x, tile.y, toTile.x, toTile.y))
					pos_left = (CELL_MARGIN + CELL_WIDTH) * tile.x + CELL_MARGIN
					pos_top = (CELL_MARGIN + CELL_HEIGHT) * tile.y + CELL_MARGIN
					xOffs = 0
					yOffs = 0
					pygame.draw.polygon(s, BLACK, self.Arrow)
					if (tile.x - toTile.x > 0): #left
						#print("left " + str(tile.x) + "," + str(tile.y))
						s = pygame.transform.rotate(s, 90)
						xOffs = -0.3
					elif (tile.x - toTile.x < 0): #right
						#print("right " + str(tile.x) + "," + str(tile.y))
						s = pygame.transform.rotate(s, 270)
						xOffs = 0.3		
					elif (tile.y - toTile.y > 0): #up
						#print("up " + str(tile.x) + "," + str(tile.y))
						yOffs = -0.3
					elif (tile.y - toTile.y < 0): #down
						#print("down " + str(tile.x) + "," + str(tile.y))
						s = pygame.transform.flip(s, False, True)
						yOffs = 0.3

			
					s.set_alpha(alpha)
					self._screen.blit(s, (pos_left + xOffs * CELL_WIDTH, pos_top + yOffs * CELL_HEIGHT))
					path = path.parent	
					alpha -= alphaDec					
					if (alpha < alphaMin):
						alpha = alphaMin
		
			for tile in self._map.ekBot.lastSearched:
				pos_left = (CELL_MARGIN + CELL_WIDTH) * tile.x + CELL_MARGIN
				pos_top = (CELL_MARGIN + CELL_HEIGHT) * tile.y + CELL_MARGIN
				pos_left_circle = int(pos_left + (CELL_WIDTH / 2))
				pos_top_circle = int(pos_top + (CELL_HEIGHT / 2))
				pygame.draw.circle(self._screen, BLACK, [pos_left_circle, pos_top_circle], int(CELL_WIDTH / 2 - 2), 12)
				pygame.draw.circle(self._screen, RED, [pos_left_circle, pos_top_circle], int(CELL_WIDTH / 2) - 5, 3)
				pygame.draw.circle(self._screen, RED, [pos_left_circle, pos_top_circle], int(CELL_WIDTH / 2) - 10, 3)
			for approx in self._map.ekBot.generalApproximations:
				if (approx[2] > 0):
					pos_left = (CELL_MARGIN + CELL_WIDTH) * approx[0] + CELL_MARGIN
					pos_top = (CELL_MARGIN + CELL_HEIGHT) * approx[1] + CELL_MARGIN
					pos_left_circle = int(pos_left + (CELL_WIDTH / 2))
					pos_top_circle = int(pos_top + (CELL_HEIGHT / 2))
					pygame.draw.circle(self._screen, BLACK, [pos_left_circle, pos_top_circle], int(CELL_WIDTH / 2 - 2), 12)
					pygame.draw.circle(self._screen, RED, [pos_left_circle, pos_top_circle], int(CELL_WIDTH / 2) - 5, 3)
					pygame.draw.circle(self._screen, RED, [pos_left_circle, pos_top_circle], int(CELL_WIDTH / 2) - 10, 3)
			#print("history")
			s = pygame.Surface((CELL_WIDTH, CELL_HEIGHT))
			s.fill(WHITE)
			s.set_colorkey(WHITE)

			pygame.draw.circle(s, BLACK, [int(CELL_WIDTH / 2), int(CELL_HEIGHT / 2)], int(CELL_WIDTH / 2 - 2), 12)
			pygame.draw.circle(s, RED, [int(CELL_WIDTH / 2), int(CELL_HEIGHT / 2)], int(CELL_WIDTH / 2) - 5, 3)
			pygame.draw.circle(s, RED, [int(CELL_WIDTH / 2), int(CELL_HEIGHT / 2)], int(CELL_WIDTH / 2) - 10, 3)
			for i in range(len(self._map.ekBot.searchHistory)):
				hist = self._map.ekBot.searchHistory[i]
				alpha = 200 - 20 * i
				s.set_alpha(alpha)
				for tile in hist:
					pos_left = (CELL_MARGIN + CELL_WIDTH) * tile.x + CELL_MARGIN
					pos_top = (CELL_MARGIN + CELL_HEIGHT) * tile.y + CELL_MARGIN
					# first, "erase" the surface by filling it with a color and
					# setting this color as colorkey, so the surface is empty
					self._screen.blit(s, (pos_left, pos_top))
			#print("surface")
			s = pygame.Surface((CELL_WIDTH, CELL_HEIGHT))
			s.fill(WHITE)
			s.set_colorkey(WHITE)
			pygame.draw.line(s, BLACK, (0, 0), (CELL_WIDTH, CELL_HEIGHT), 4)
			pygame.draw.line(s, RED, (0, 0), (CELL_WIDTH, CELL_HEIGHT), 2)
			pygame.draw.line(s, BLACK, (0, CELL_HEIGHT), (CELL_WIDTH, 0), 4)
			pygame.draw.line(s, RED, (0, CELL_HEIGHT), (CELL_WIDTH, 0), 2)
			#print("val")
			if (self._map != None and self._map.ekBot != None and self._map.ekBot.evaluatedGrid != None and len(self._map.ekBot.evaluatedGrid) > 0):
				#print("if")
				for row in range(self._map.rows):
					for column in range(self._map.cols):		
						#print("loop")
						countEvaluated = int(self._map.ekBot.evaluatedGrid[column][row] + self._map.ekBot.lastEvaluatedGrid[column][row]);
						#print("loopVal")
						if (countEvaluated > 0):					
							#print("CountVal: {},{}: {}".format(column, row, countEvaluated))
							pos_left = (CELL_MARGIN + CELL_WIDTH) * column + CELL_MARGIN
							pos_top = (CELL_MARGIN + CELL_HEIGHT) * row + CELL_MARGIN
							alpha = int(75 + countEvaluated * 3)
							s.set_alpha(alpha if alpha < 255 else 255)
							self._screen.blit(s, (pos_left, pos_top))
			#print("deltas")
			#print("drawing deltas")
			# Draw deltas
			for row in range(self._map.rows):
				for column in range(self._map.cols):
					tile = self._map.grid[row][column]
					pos_left = (CELL_MARGIN + CELL_WIDTH) * column + CELL_MARGIN
					pos_top = (CELL_MARGIN + CELL_HEIGHT) * row + CELL_MARGIN

					if (tile.delta.toTile != None):
						if (tile.x - tile.delta.toTile.x > 0): #left
							#print("left " + str(tile.x) + "," + str(tile.y))
							pygame.draw.polygon(self._screen, GRAY_DARK, [(pos_left + CELL_WIDTH / 4, pos_top), (pos_left + CELL_WIDTH / 4, pos_top + CELL_HEIGHT), (pos_left - CELL_WIDTH / 4, pos_top + CELL_HEIGHT / 2)])
						elif (tile.x - tile.delta.toTile.x < 0): #right
							#print("right " + str(tile.x) + "," + str(tile.y))
							pygame.draw.polygon(self._screen, GRAY_DARK, [(pos_left + 3 * CELL_WIDTH / 4, pos_top), (pos_left + 3 * CELL_WIDTH / 4, pos_top + CELL_HEIGHT), (pos_left + 5 * CELL_WIDTH / 4, pos_top + CELL_HEIGHT / 2)])			
						elif (tile.y - tile.delta.toTile.y > 0): #up
							#print("up " + str(tile.x) + "," + str(tile.y))
							pygame.draw.polygon(self._screen, GRAY_DARK, [(pos_left, pos_top + CELL_HEIGHT / 4), (pos_left + CELL_WIDTH, pos_top + CELL_HEIGHT / 4), (pos_left + CELL_WIDTH / 2, pos_top - CELL_HEIGHT / 4)])	
						elif (tile.y - tile.delta.toTile.y < 0): #down
							#print("down " + str(tile.x) + "," + str(tile.y))
							pygame.draw.polygon(self._screen, GRAY_DARK, [(pos_left, pos_top + 3 * CELL_HEIGHT / 4), (pos_left + CELL_WIDTH, pos_top + 3 * CELL_HEIGHT / 4), (pos_left + CELL_WIDTH / 2, pos_top + 5 * CELL_HEIGHT / 4)])			



			#print("drawing text")
			#draw text
			for row in range(self._map.rows):
				for column in range(self._map.cols):
					tile = self._map.grid[row][column]	
					pos_left = (CELL_MARGIN + CELL_WIDTH) * column + CELL_MARGIN
					pos_top = (CELL_MARGIN + CELL_HEIGHT) * row + CELL_MARGIN
					color = WHITE
					color_font = WHITE
					if tile.ismountain(): # Mountain
						color = BLACK
					elif tile.player >= 0:
						playercolor = PLAYER_COLORS[tile.player]
						colorR = playercolor[0]
						colorG = playercolor[1]
						colorB = playercolor[2]				
						if (tile.isCity or tile.isGeneral):
							colorR = colorR + KING_COLOR_OFFSET if colorR <= 255 - KING_COLOR_OFFSET else 255
							colorG = colorG + KING_COLOR_OFFSET if colorG <= 255 - KING_COLOR_OFFSET else 255
							colorB = colorB + KING_COLOR_OFFSET if colorB <= 255 - KING_COLOR_OFFSET else 255
						if (not tile.isvisible()): 
							colorR = colorR / 2 + 40
							colorG = colorG / 2 + 40
							colorB = colorB / 2 + 40
						color = (colorR, colorG, colorB)
					elif tile.isobstacle(): # Obstacle
						color = GRAY_DARK
					elif not tile.isvisible(): 
						color = GRAY
					else:
						color_font = BLACK
					# Draw Text Value
					if (tile.army != 0 and tile.discovered): # Don't draw on empty tiles
						textVal = str(tile.army)
						self._screen.blit(self._font.render(textVal, True, color_font), (pos_left + 2, pos_top + CELL_HEIGHT / 4))			
					# Draw delta
					if (tile.delta.armyDelta != 0): # Don't draw on empty tiles
						textVal = str(tile.delta.armyDelta)
						self._screen.blit(self._fontSmall.render(textVal, True, color_font), (pos_left + 2, pos_top + CELL_HEIGHT / 2))
					# Draw coords					
					textVal = "{},{}".format(tile.x, tile.y)
					self._screen.blit(self._fontSmall.render(textVal, True, color_font), (pos_left, pos_top - 2))

			#print("replay {} turn {}".format(self.repId, self._map.turn))
			# Limit to 60 frames per second
			self._clock.tick(60)
 
			# Go ahead and update the screen with what we've drawn.
			pygame.display.flip()
		except:
			print("Unexpected error:", sys.exc_info()[0])
	

	def save_image(self):		
		while True:
			if self._readyRender:
				#self.images.append(("{}\\{}.bmp".format(self.logDirectory, self._map.turn), pygame.image.tostring(self._screen, "RGB")))
				
				pygame.image.save(self._screen, "{}\\{}.png".format(self.logDirectory, self._map.turn))
				self._readyRender = False
			time.sleep(0.1)