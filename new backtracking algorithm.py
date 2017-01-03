from pykinect2 import PyKinectV2, PyKinectRuntime
from pykinect2.PyKinectV2 import *
import ctypes
import _ctypes
import pygame
import sys
import math
import copy
import speech_recognition as sr
import time

class GameRuntime(object): #general framework for this script came from kinect workshop
    def __init__(self):
        pygame.init()
        self.screen_width = 1920
        self.screen_height = 1080
        # Used to manage how fast the screen updates
        self._clock = pygame.time.Clock()
        # Set the width and height of the window [width/2, height/2]
        self._screen = pygame.display.set_mode((960,540), pygame.HWSURFACE|pygame.DOUBLEBUF, 32)
        # Loop until the user clicks the close button.
        self._done = False
        # Kinect runtime object, we want color and body frames 
        self._kinect = PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameSourceTypes_Color | 
            PyKinectV2.FrameSourceTypes_Body)
        # back buffer surface for getting Kinect color frames, 32bit color,
        # width and height equal to the Kinect color frame size
        self._frame_surface = pygame.Surface((self._kinect.color_frame_desc.Width, 
            self._kinect.color_frame_desc.Height), 0, 32)
        # here we will store skeleton data 
        self._bodies = None
        #initialize what movement mode we are in 
        self.mode = None
        #initialize velocity vectors for robot
        self.contents = "0 0 0 0"
        #initailize velocity vetors to be zero so it starts out still
        #first digit is left/right, 2nd digit is up/down, 3rd digit is twisting, 4th digit is also up/down
        self.state = None
        #this variable gets switched on the people dodgin game is played
        self.dirs = ["1 0 0 0","-1 0 0 0","0 1 0 0","0 -1 0 0"]
        #cardinal directions that the robot loops through as it recursively backtracks through the people dogding game
        self.minLegalDistance = 2
        #If the robot it closer than one meter to a person, then a move is illegal
        self.relativePosition = [0,0]
        #keeps track of how far the robot has moved (relatively) in the x and y directions
        self.relativePositionRange = 5
        #sets a wall for how far the robot can move left and right, effectively establishing walls to the maze
        self.moveTime = 13000
        #the number of move commands which get sent to the robot every time it has to move so that the robot
        #can take a few steps before it reevaluates the legality of a move
        self.bodiesPresent = 0
        #number of bodies on the screen at any given point in time
        self.closeBody = None
        #body obect robot tracks during game
        self.closeBodyJoints = None
        #skeleton of body object that the robot tracks
        self.prevDir = "0 0 0 0"
        #the last move the robot made during the backtracking maze, initialized to zero velocities
        self.moveDir = "0 0 0 0"
        #current move the robot is making during the backtracking maze, initialized to zero velocities
        self.solveRequest = False
        #boolean which flips on if 
        self.moving = False
        #boolean move flag
        self.startMoveTime = None
        #starts a counter for how long the robot wil move for in game mode
        self.lengthMoveTime = 3.5
        #actual duration of each move in game mode
        self.notTrackedCount = 0
        #counter for how many instances the robot has lost all users
        self.maxNotTrackedCount = 800
        #number of iterations before the robot declares it is lost
        self.isDone = False
        #boolean flag to end game mode
        self.winCount = 0
        #this variable gets + 1 if thr robot moves forward and -1 if the robot moves backwards
        self.maxWinCount = 5
        self.gameNotTrackedCount = 0
        self.pauseState = False
        self.maxGameNotTrackedCount = 1300
    def draw_color_frame(self, frame, target_surface): #this function came from kinect workshop
        #draw the rgb stream into the pygame surface
        target_surface.lock()
        address = self._kinect.surface_as_array(target_surface.get_buffer())
        ctypes.memmove(address, frame.ctypes.data, frame.size)
        del address
        target_surface.unlock()

    def run(self):
        def writeFile(path, contents): #from course website
            with open(path, "wt") as f:
                f.write(contents)

        def readFile(path): #from course website
            with open(path, "rt") as f:
                return f.read()

        def lostPlayer(rightHandState,leftHandState):
            return (rightHandState == 0 or rightHandState == 1) or (leftHandState == 0 or leftHandState == 1)
                #checking to see if the kinect is tracking the hands;sometimes it loses sight of one or both of 
                #the hands and then the robot cannot be controlled because you cannot update the last command

        def findLeader(depthList):
            #finds the guy who is farthest away from the kinect sensor
            maxDepth = None
            currDepth = None
            for i in range(len(depthList)):
                #loops thru depth list, which is a 2d list containing everyone who is being tracked,
                #and how far away they are from the sensor
                currDepth = depthList[i][0]
                if maxDepth == None:
                    maxDepth = currDepth
                if currDepth > maxDepth:
                    maxDepth = currDepth
                    j = i
                else: 
                    j = 0
            return depthList[j][1]
            #returns the body object of the individual farthest away from the camera

        def findFollower1(depthList):
            #finds tha person who is closest to the camera
            minDepth = None
            currDepth = None
            for i in range(len(depthList)):
                currDepth = depthList[i][0]
                if minDepth == None:
                    minDepth = currDepth
                if currDepth < minDepth:
                    minDepth = currDepth
                    j = i
                else: 
                    j = 0
            return depthList[j][1]
            #returns the body obect of the individual closest to the camera
        def findFollower2(depthList):
            #find the third guy who is of intermediate distance
            peopleDict = {}
            findFollower2List = []
            for i in depthList: 
                peopleDict[i[0]] = i[1]
            #dictionary with keys for depth
            sortedPeopleDict = sorted(peopleDict)
            #sort the keys into a nice list
            for key in sortedPeopleDict:
                findFollower2List.append(key)
            follower2 = findFollower2List[1]
            #the individual we want is the 1th element of the findfollower2list
            return peopleDict[follower2]
            #returns the body object of the individual who is of intermediate distance 
            #away from the camer

        def allPlayersLost(allLost):
            return allLost == 6
            #only returns true when the camera is tracking zero bodies

        def lostPlayer(rightHandState,leftHandState):
            return (rightHandState == 0 or rightHandState == 1) or (leftHandState == 0 or leftHandState == 1)
                #checking to see if the kinect is tracking the hands;sometimes it loses sight of one or both of 
                #the hands and then the robot cannot be controlled because you cannot update the last command

        def haltOverride(self):
        	return self.mode == "halt"
            #returns true when the current mode is 'halt'

        def zAlligned(leaderDistance,forwardsDistance,backwardsDistance):
            if backwardsDistance <= leaderDistance and leaderDistance <= forwardsDistance:
                return True
            else: 
                return False
            #returns true when the leader body is at a happy distance from the kinect
            #as described by the forward and backwards distances

        def notAllignedBack(leaderDistance,forwardsDistance,backwardsDistance):
            if leaderDistance < backwardsDistance:
                return True
            else:
                return False
            #returns true when the leader body is too close to the kinect as described
            #by the backwards distance

        def notAllignedForward(leaderDistance,forwardsDistance,backwardsDistance):
            if leaderDistance > forwardsDistance:
                return True
            else:
                return False
            #returns true when the leader body is too far away from the kinect as 
            #described the forwards distance

        def xAlligned(leaderXOffset,leftDistance,rightDistance):
            if leftDistance <= leaderXOffset <= rightDistance:
                return True
            else:
                return False 
            #returns true if the leader's x position is within left and right distance

        def notAllignedLeft(leaderXOffset,leftDistance,rightDistance):
            if leftDistance >= leaderXOffset:
                return True
            else:
                return False
            #returns true when the leader's x position is less than left distance

        def notAllignedRight(leaderXOffset,leftDistance,rightDistance):
            if rightDistance <= leaderXOffset:
                return True
            else:
                return False
            #returns true when the leaders x position is greater than right distance

        def isClose(val1,val2):
            if abs(val1-val2) <= 0.03:
                return True
            else:
                return False
            #helper function to determine if the game gesture was made
            
        def isLegal(self):
            print("checking legality")
            if self.closeBodyJoints[PyKinectV2.JointType_KneeRight].Position.z < self.minLegalDistance:
                print("prevDir:",self.prevDir)
                print("not legal")
                #robot must mantain a min distance from all players
                return False
            print("legal move")
            return True
            #distance maintained;returns true

        def getNextDirection(self):
            self.state = "game"
            #this function examines the current prevDir and cycles the robot to the next possible move
            #sort of similar to backtracking
            if self.prevDir == "0 0 0 0":
                self.winCount += 1
                newDir = "0 -1 0 0"
            elif self.prevDir == "0 1 0 0":
                newDir = "1 0 0 0"
            elif self.prevDir == "1 0 0 0":
                newDir = "-1 0 0 0"
            elif self.prevDir == "-1 0 0 0":
                self.winCount -= 1
                newDir = "0 1 0 0"
            elif self.prevDir == "0 1 0 0":
                newDir = "1 0 0 0"
            self.prevDir = newDir
            print("newDir:",newDir)
            return newDir

        def backTrack(self):
            #this helper function examines what the last moveDir was and reverses it
            #this function is only called when the robot makes an illegal move or after 
            #backtracking into an illegal move
            self.state = "game"
            print("backtracking")
            print('moveDir backtrack:',self.moveDir)
            if self.moveDir == "0 0 0 0":
                print("weird situation")
                return "0 0 0 0"
            if self.moveDir == "0 1 0 0":
                print("hit")
                return "0 -1 0 0"
            elif self.moveDir == "0 -1 0 0":
                return "1 0 0 0"
            elif self.moveDir == "1 0 0 0":
                return "-1 0 0 0"
            elif self.moveDir == "-1 0 0 0":
                return "1 0 0 0"
            
                
        def getAlgorithmCommand(self):
            if not isLegal(self):
                direction = backTrack(self)
                return ("move",direction)
            print("wincount:",self.winCount)
            if self.winCount > self.maxWinCount:
                self.winCount = 0
                direction = "0 0 0 0"
                return ("solved",direction)
            self.prevDir = "0 0 0 0"
            direction = getNextDirection(self)
            return ("move",direction)

        def nextSolveStep(self):
            (command,direction) = getAlgorithmCommand(self)
            if command == "move":
                self.moveDir = direction
                print("next solve said:",self.moveDir)
                self.moving = True
                self.startMoveTime = time.time()
                self.state = "game"
                #writeFile('speed.txt',self.moveDir)
                #print("                                                 in the middle:",readFile('speed.txt'))

                return 
            if command == "solved":
                self.moving = False
                self.solveRequest = True
                self.isDone = True
                print("made it")
                # for time in range(self.moveTime):
                #     writeFile('speed.txt',"0 1 0 0")
                writeFile('speed.txt',"0 0 0 0")
                return "solved gang!"

        #initialize local variables for the control loop
        count = 0
        lostCount = 0
       
        spinTime = 2000
        prevState = None
        forwardsDistance = 5
        backwardsDistance = 4
        leftDistance = -0.3
        rightDistance = 0.3
        maxLostCount = 400        
        # -------- Main Program Loop -----------
        while not self._done:
            # --- Main event loop
            for event in pygame.event.get(): # User did something
                if event.type == pygame.QUIT: # If user clicked close
                    self._done = True # Flag that we are done so we exit this loop
            # We have a color frame. Fill out back buffer surface with frame's data 
            if self._kinect.has_new_color_frame():
                frame = self._kinect.get_last_color_frame()
                self.draw_color_frame(frame, self._frame_surface)
                frame = None
            # We have a body frame, so can get skeletons
            if self._kinect.has_new_body_frame(): 
                self._bodies = self._kinect.get_last_body_frame()
                if self._bodies is not None: 
                    text1 = readFile('contact.txt')
                    #read file that the speech recognition is writing to
                    
                    if text1 == "contact right":
                        #someone said 'contact right'
                        self.contents = "0 0 1 0"
                        #Update the contents so that the robot will spin clockwise
                        for time in range(spinTime):
                            writeFile('speed.txt',self.contents)
                            #only writes the file for spinTime number of iterations; spinTime = 2800
                            #provides an approximately 90 degree turn 
                        self.contents = "0 0 0 0"
                        
                        #tell the robot to stop
                        print(readFile('speed.txt'),readFile('contact.txt'))
                        writeFile('contact.txt',"")
                        writeFile("speed.txt","0 0 0 0")
                        #reset the contact text file so that it doesnt enter this if statement more than once per
                        #spoken phrase (if you dont reset it, it will continue to spin because it thinks someone
                        #is saying contact right constantly)
                        writeFile('height.txt',"0")
                        #drop the height of the chassis so that the robot 'takes cover'
                    if text1 == "contact left":
                        #disturbingly similar to contact right situation
                        self.contents = "0 0 -1 0"
                        for time in range(spinTime):
                            writeFile('speed.txt',self.contents)
                        self.contents = "0 0 0 0"
                        writeFile('speed.txt',self.contents)
                        print(readFile('speed.txt'),readFile('contact.txt'))
                        writeFile('contact.txt',"")
                        writeFile('height.txt',"0")
                    if text1 == "contact front":  
                        #similar to contact right and contact left, but the robot does not need to spin                         
                        self.contents = "0 0 0 0"
                        writeFile('speed.txt',self.contents)
                        print(readFile('speed.txt'),readFile('contact.txt'))  
                        writeFile('contact.txt',"") 
                        writeFile('height.txt',"0")
                    if text1 == "Rush":
                        #someone said rush, the robot now needs to charge forward until told to stop
                        self.contents = "0 -1 0 0"
                        
                        writeFile('height.txt',"1")
                        for time in range(2000):
                            writeFile('speed.txt',self.contents)
                        writeFile('speed.txt',"0 0 0 0")
                    if text1 == "stop":
                        self.contents = "0 0 0 0"
                        writeFile('speed.txt',self.contents)
                        writeFile('contact.txt',"")
                    depthList = []
                    bodyList = []
                    self.bodiesPresent = 0
                    #must be set to zero before entering the body assignment loop
                    allLost = 0
                    for i in range(0, self._kinect.max_body_count):
                        print("speed at top:",readFile('speed.txt'))
                        #loop thru the six possible people it could potentially track
                        if i == 0:
                            body0 = self._bodies.bodies[i]
                            if body0.is_tracked:
                                joints0 = body0.joints
                                self.bodiesPresent +=1
                                #it is useful to know how many bodies are being tracked at a given point in time
                                depthList.append([joints0[PyKinectV2.JointType_HipLeft].Position.z,body0]) 
                                #add body to the depthlist in order to recieve a unique variable name
                            else:
                                allLost += 1
                                #adds to variable which will determine whether or not nobody is being tracked
                        if i == 1:
                            body1 = self._bodies.bodies[i]
                            if body1.is_tracked:
                                joints1 = body1.joints
                                self.bodiesPresent +=1
                                depthList.append([joints1[PyKinectV2.JointType_HipLeft].Position.z,body1])
                                #add body to the depthlist in order to recieve a unique variable name
                            else:
                                allLost += 1
                                #adds to variable which will determine whether or not nobody is being tracked
                        if i == 2:
                            body2 = self._bodies.bodies[i]
                            if body2.is_tracked:
                                joints2 = body2.joints
                                self.bodiesPresent +=1
                                depthList.append([joints2[PyKinectV2.JointType_HipLeft].Position.z,body2])
                                #add body to the depthlist in order to recieve a unique variable name
                            else:
                                allLost += 1
                                #adds to variable which will determine whether or not nobody is being tracked
                        if i == 3:
                            body3 = self._bodies.bodies[i]
                            if body3.is_tracked:
                                joints3 = body3.joints
                                self.bodiesPresent +=1
                                depthList.append([joints3[PyKinectV2.JointType_HipLeft].Position.z,body3])
                                #add body to the depthlist in order to recieve a unique variable name
                            else:
                                allLost += 1
                                #adds to variable which will determine whether or not nobody is being tracked
                        if i == 4:
                            body4 = self._bodies.bodies[i]
                            if body4.is_tracked:
                                joints4 = body4.joints
                                self.bodiesPresent +=1
                                depthList.append([joints4[PyKinectV2.JointType_HipLeft].Position.z,body4])
                                #add body to the depthlist in order to recieve a unique variable name
                            else:
                                allLost += 1
                                #adds to variable which will determine whether or not nobody is being tracked
                        if i == 5:
                            body5 = self._bodies.bodies[i]
                            if body5.is_tracked:
                                joints5 = body5.joints
                                self.bodiesPresent +=1
                                depthList.append([joints5[PyKinectV2.JointType_HipLeft].Position.z,body5])
                                #add body to the depthlist in order to recieve a unique variable name
                            else:
                                allLost += 1
                                #adds to variable which will determine whether or not nobody is being tracked
                        if self.bodiesPresent == 0:
                            #nobody is being tracked
                            if self.notTrackedCount >= self.maxNotTrackedCount and self.state != "game":
                                #only sends stop signal if operators are out of frame for an extended period of time
                                writeFile('speed.txt',"0 0 0 0")
                                self.notTrackedCount = 0
                                #reset notTrackedcount
                                print("lost")
                                self.mode = "operators not tracked"
                                #update mode
                            if self.bodiesPresent == 0: 
                                self.notTrackedCount += 1
                                print("nt:",self.notTrackedCount)
                                #only add to the count when noone is tracked
                                if self.state != "game":
                                    print("skipped")
                                    continue
                            else: self.notTrackedCount = 0
                                #jump back to the top of the loop; if we dont continue here code will crash as you will
                                #be requesting information from bodies and skeletons that do not exist
                        if self.bodiesPresent != 0 or self.state == "game":
                            self.notTrackedCount = 0
                            #reset nottrackedcount
                            if self.bodiesPresent != 0:
                                leaderBody = findLeader(depthList)
                                #leaderBody is now the ID for the body that is furthest away from the camera
                                leaderJoints = leaderBody.joints
                                #leaderJoints is now the ID for the skeleton of leaderBody
                                leaderDistance = leaderJoints[PyKinectV2.JointType_KneeRight].Position.z
                                leaderXOffset = leaderJoints[PyKinectV2.JointType_SpineMid].Position.x
                                #leaderDistance is how far away the leader is from the kinect
                                bodyIsLost = lostPlayer(leaderBody.hand_right_state,leaderBody.hand_left_state)
                                #bodyIsLost will equal True when the leader's hands are not being tracked
                                # if bodyIsLost:
                                #     # lostCount += 1
                                if not bodyIsLost:
                                    lostCount = 0
                                if (isClose(leaderJoints[PyKinectV2.JointType_HandRight].Position.x,leaderJoints[PyKinectV2.JointType_ShoulderLeft].Position.x)
                                    and isClose(leaderJoints[PyKinectV2.JointType_HandRight].Position.y,leaderJoints[PyKinectV2.JointType_ShoulderLeft].Position.y)):
                                    #player made the game gesture and we flip the demo into Game mode!
                                    self.state = "game"
                                if (leaderBody.hand_left_state == 3 and (leaderJoints[PyKinectV2.JointType_Head].Position.y <= 
                                leaderJoints[PyKinectV2.JointType_HandLeft].Position.y)):
                                    self.state = "game"
                                    #backup gesture to flip into game mode!
                            if self.state == "game":
                                print("game state")
                                self.mode = "game"
                                #displays 'game' mode to pygame window
                                # self.contents = "0 0 0 0"
                                if self.bodiesPresent != 0:
                                    self.closeBody = findFollower1(depthList)
                                    self.closeBodyJoints = self.closeBody.joints
                                #pass this guy into solve function so it will be constantly updated as the robot
                                # writeFile('speed.txt',self.contents)
                                #stop the robot and get ready to play the dodging person game
                                import time
                                print(text1)
                                if text1 == "start":
                                    print("tthere")
                                    self.solveRequest = True
                                    
                                    print("moving?",self.moving,"solvReq:",self.solveRequest,"pauseState?",self.pauseState)
                                    if self.pauseState:
                                        if self.bodiesPresent == 0:
                                            self.gameNotTrackedCount += 1
                                            self.moving = False
                                            self.solveRequest = False
                                            print('GTN:',self.gameNotTrackedCount)
                                        if self.gameNotTrackedCount > self.maxGameNotTrackedCount:
                                            self.pauseState = False
                                            print('reset count we made it')
                                            self.gameNotTrackedCount = 0
                                            self.isDone = True
                                            self.moving = False
                                            self.solveRequest = True
                                        if self.bodiesPresent != 0:
                                            print('     reset')
                                            self.pauseState = False
                                            self.gameNotTrackedCount = 0
                                            self.solveRequest = True
                                    if self.moving == True:
                                        print("here")
                                        self.solveRequest = False
                                        writeFile('speed.txt',self.moveDir)
                                        print("                     speed at bottom:",readFile('speed.txt'))
                                        print("moving",self.moveDir,self.bodiesPresent,self.closeBodyJoints[PyKinectV2.JointType_KneeRight].Position.z,"NT:",self.notTrackedCount)
                                        
                                        if (time.time() - self.startMoveTime > self.lengthMoveTime):

                                            print("time")
                                            self.solveRequest = True
                                            self.moving = False

                                            print("paused")
                                            #self.moveDir = "0 0 0 0"
                                            writeFile('speed.txt',"0 0 0 0")
                                            if self.bodiesPresent == 0:
                                                self.pauseState = True
                                                self.moving = False
                                                self.gameNotTrackedCount += 1
                                                self.solveRequest = False
                                                print("GTN:",self.gameNotTrackedCount)
                                    if self.solveRequest:
                                        if self.isDone:
                                            # self.mode = "victory"
                                            print("gang gang")
                                            for time in range(self.moveTime):
                                                writeFile('speed.txt',"0 -1 0 0")
                                                print("gaaaang")
                                            writeFile("speed.txt","0 0 0 0")
                                            self.state = None
                                        else:
                                            print("trying next step")
                                            nextSolveStep(self)
                                            print("moving?",self.moving,"moveDir:",self.moveDir)

                                    #tries to backtrack through the people game
                                    #reset contact text file so that it doesnt perpetually play the game                             
                            if lostCount >= maxLostCount and (self.state == None):
                                #if the robot can't see your hands for a prolonged amount of time
                                self.mode = "hands not tracked"
                                self.contents = "0 0 0 0"
                                writeFile('speed.txt',self.contents)   
                                print(self.mode,readFile('speed.txt'))                            
                            if leaderBody.hand_right_state == 3 and (leaderJoints[PyKinectV2.JointType_Head].Position.y <= 
                            leaderJoints[PyKinectV2.JointType_HandRight].Position.y) and (self.state == None): # leader throws halt gesture
                                self.mode = "halt"
                                self.contents = "0 0 0 0"
                                writeFile('speed.txt',self.contents)
                                print(readFile('speed.txt'),"halt")
                                #send stop signal
                            if notAllignedBack(leaderDistance,forwardsDistance,backwardsDistance) and (self.state == None):
                                if leaderBody.hand_right_state == 3 and (leaderJoints[PyKinectV2.JointType_Head].Position.y <= 
                                    leaderJoints[PyKinectV2.JointType_HandRight].Position.y):
                                    self.contents = "0 0 0 0"
                                    self.mode = "halt"
                                    #checks to see if the leader is displaying halt gesture
                                else:	
                                    if lostCount < maxLostCount:
                                        self.mode = "move backwards"
                                        self.contents = "0 1 0 0"
	                                #leader is not displaying halt; move backwards	                     
                                writeFile('speed.txt',self.contents)
                                print(self.mode,readFile('speed.txt'))       
                            if zAlligned(leaderDistance,forwardsDistance,backwardsDistance) and (self.state == None):
                                # if notAllignedLeft(leaderXOffset,leftDistance,rightDistance):
                                #     if leaderBody.hand_right_state == 3 and (leaderJoints[PyKinectV2.JointType_Head].Position.y <= 
                                #     leaderJoints[PyKinectV2.JointType_HandRight].Position.y):
                                #         self.contents = "0 0 0 0"
                                #         self.mode = "halt"
                                #         writeFile('speed.txt',self.contents)
                                #         print(self.mode,readFile('speed.txt'))
                                #         #checks to see if the leader is displaying halt gesture
                                #     else:
                                #         if lostCount < maxLostCount:
                                #             self.contents = "1 0 0 0"
                                #             self.mode = "move left"
                                #             writeFile('speed.txt',self.contents)
                                #             print(self.mode,readFile('speed.txt'))
                                #         #leader is not displaying halt; move to the left
                                # if notAllignedRight(leaderXOffset,leftDistance,rightDistance):
                                #     if leaderBody.hand_right_state == 3 and (leaderJoints[PyKinectV2.JointType_Head].Position.y <= 
                                #     leaderJoints[PyKinectV2.JointType_HandRight].Position.y):
                                #         self.contents = "0 0 0 0"
                                #         self.mode = "halt"
                                #         writeFile('speed.txt',self.contents)
                                #         print(self.mode,readFile('speed.txt'))
                                #         #checks to see if the leader is displaying halt gesture
                                #     else:
                                #         if lostCount < maxLostCount:
                                #             self.contents = "-1 0 0 0"
                                #             self.mode = "move right"
                                #             writeFile('speed.txt',self.contents)
                                #             print(self.mode,readFile('speed.txt'))
                                #         #leader is not displaying halt; move to the right
                                if xAlligned(leaderXOffset,leftDistance,rightDistance):
                                    if leaderBody.hand_right_state == 3 and (leaderJoints[PyKinectV2.JointType_Head].Position.y <= 
                                    leaderJoints[PyKinectV2.JointType_HandRight].Position.y):
                                        self.contents = "0 0 0 0"
                                        self.mode = "halt"
                                        writeFile('speed.txt',self.contents)
                                        print(self.mode,readFile('speed.txt'))
                                        #checks to see if the leader is displaying halt gesture
                                    else:
                                        if lostCount < maxLostCount:
                                            self.contents = "0 0 0 0"
                                            self.mode = "stop"
                                            writeFile('speed.txt',self.contents)
                                            print(self.mode,readFile('speed.txt'))
                                        #leader is not displaying halt; but stay still anyways
                            if notAllignedForward(leaderDistance,forwardsDistance,backwardsDistance) and (self.state == None):
                            	if leaderBody.hand_right_state == 3 and (leaderJoints[PyKinectV2.JointType_Head].Position.y <= 
                            		leaderJoints[PyKinectV2.JointType_HandRight].Position.y):
                                    self.contents = "0 0 0 0"
                                    self.mode = "halt" 
                                    writeFile('speed.txt',self.contents)
                                    print(self.mode,readFile('speed.txt')) 
                                    #checks to see if the leader is displaying halt gesture                                 
                            	else:
                                    if lostCount < maxLostCount:
                                        self.mode = "move forward"
                                        self.contents = "0 -1 0 0"              
                                        writeFile('speed.txt',self.contents)
                                        print(self.mode,readFile('speed.txt'))
                                    #leader is not displaying halt; move to forwards
                            if self.bodiesPresent == 2 and (self.state == None):
                                #still tracking the leader, but it is also paying attention to the other guy
                                #and whether or not he throws a halt gesture
                                follower1Body = findFollower1(depthList)
                                #unique ID for follower1 bodyobject
                                follower1Joints = follower1Body.joints
                                #ID for the skeleton of follower1Body
                                if follower1Body.hand_right_state == 3 and (follower1Joints[PyKinectV2.JointType_Head].Position.y <= 
                            		follower1Joints[PyKinectV2.JointType_HandRight].Position.y):
                                    self.contents = "0 0 0 0"
                                    self.mode = "halt"
                                    writeFile('speed.txt',self.contents)
                                    print(self.mode,readFile('speed.txt'))
                                    #checks to see if follower1 throws a halt gesture
                            if self.bodiesPresent == 3 and (self.state == None):
                                follower1Body = findFollower1(depthList)
                                #rename this guy because he may have changed
                                follower1Joints = follower1Body.joints
                                follower2Body = findFollower2(depthList)
                                #unique ID for follower2's body object
                                follower2Joints = follower2Body.joints
                                #unique ID for follower2 skeleton
                                if ((follower1Body.hand_right_state == 3) and (follower1Joints[PyKinectV2.JointType_Head].Position.y <= 
                            		follower1Joints[PyKinectV2.JointType_HandRight].Position.y)) or (follower2Body.hand_right_state == 3 and (follower2Joints[PyKinectV2.JointType_Head].Position.y <= follower2Joints[PyKinectV2.JointType_HandRight].Position.y)):
                                    self.contents = "0 0 0 0"
                                    self.mode = "halt"
                                    writeFile('speed.txt',self.contents)
                                    print(self.mode,readFile('speed.txt'))
                                    #checks to see if follower2 or follower1 throws halt gesture                      
            # Optional debugging text
            font = pygame.font.Font(None, 200)
            text = font.render(str(self.mode), 1, (0, 0, 0))
            self._frame_surface.blit(text, (100,100))
            # --- copy back buffer surface pixels to the screen, resize it if needed and keep aspect ratio
            # --- (screen size may be different from Kinect's color frame size) 
            h_to_w = float(self._frame_surface.get_height()) / self._frame_surface.get_width()
            target_height = int(h_to_w * self._screen.get_width())
            surface_to_draw = pygame.transform.scale(self._frame_surface, (self._screen.get_width(), target_height));
            self._screen.blit(surface_to_draw, (0,0))
            surface_to_draw = None
            pygame.display.update()
            # --- Limit to 60 frames per second
            self._clock.tick(60)
        # Close our Kinect sensor, close the window and quit.
        self._kinect.close()
        pygame.quit()
game = GameRuntime();
game.run();
print("Gaaaaaaaaaaaaaaaaaaaaaaaaannnnnnnnnnnnnnnnnnnnnnnnnngggggggggggggggggggggggggggggg")