# Hand-Signal-Code
Python script for the snake monster hand signal control system

Depedencies: Microsoft Kinect V2, Google speech to text API
Python Modules: pykinect2, ctypes, _ctypes, pygame, speech_recognition, time, copy, math, sys

Description: This script takes in the IR and RGB stream from the kinect and uses the pykinect module to retrieve skeletons and assign them 
unique IDs in real time for up to three bodies at once.

The script writes and reads from three text files: speed, contact, and height. 
the speed.txt files contains four numbers which pertain to different movement directions and velocities.

Movement number description for speed.txt:
Move Forward: "0 1 0 0"
Move Backward: "0 -1 0 0" 
Move Right: "1 0 0 0"
Move Left: "-1 0 0 0"
Spin clockwise: "0 0 1 0"
Spin counter-clockwise: "0 0 -1 0"
Stationary: "0 0 0 0"

The height.txt file contains a binary 0 or 1; zero for crouched, one for standing.

The contact.txt file contains whatever the last word spoken to the snake monster was.

The snakeMonsterWalking matlab code works the same except it reads from speed.txt and contact.txt instead of the joystick inputs

