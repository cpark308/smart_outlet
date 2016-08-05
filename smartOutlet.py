import json, requests
import Adafruit_BBIO.GPIO as GPIO
import time
from threading import Timer, Thread, Event
from datetime import datetime
from pytz import timezone

timetoken = '0'
url = 'http://pubsub.pubnub.com/subscribe/sub-c-ef558a8a-2444-11e6-be83-0619f8945a4f/smartOutlet/0/'

outletPin = ['P8_11', 'P8_13', 'P8_15', 'P8_17']

GPIO.setwarnings(False)
GPIO.cleanup()
for i in range(0, 4):
	print "pin init:", i
	GPIO.setup(outletPin[i], GPIO.OUT)
	GPIO.output(outletPin[i], GPIO.LOW)
	time.sleep(1)
	GPIO.output(outletPin[i], GPIO.HIGH)

class durationThread(Thread):
	def __init__(self, event):
		Thread.__init__(self)
		self.stopped = event
	def run(self):
		while not self.stopped.wait(1):
			durationOnff()

class scheduleThread(Thread):
	def __init__(self, event):
		Thread.__init__(self)
		self.stopped = event
	def run(self):
		while not self.stopped.wait(60):
			scheduleOnff()

durOngoing = [0,0,0,0]
durStatus = [0,0,0,0]
durSeconds = [0,0,0,0]

def durationOnff():
	for i in range(0, 4):
		if durOngoing[i] == 1:
			if durSeconds[i] == 0:
				durOngoing[i] = 0
				if durStatus[i] == 1:
					GPIO.output(outletPin[i], GPIO.HIGH)
				else:
					GPIO.output(outletPin[i], GPIO.LOW)
			else:
				durSeconds[i] -= 1

schedOnceOngoing = [0,0,0,0]
schedOnceStatus = [0,0,0,0]
schedOnceStart = ['0','0','0','0']
schedOnceEnd = ['0','0','0','0']

def scheduleOnff():
	central = timezone('US/Central')
	currentDateTime = datetime.now(central)
	currentTime = str(currentDateTime.time().hour) + ":"
	if currentDateTime.time().minute < 10:
		currentTime += "0" + str(currentDateTime.time().minute)
	else:
		currentTime += str(currentDateTime.time().minute)
	print currentTime
	currentDay = str(currentDateTime.weekday() + 1)
	
	for i in range (0, 4):
		if schedOnceOngoing[i] == 1:
			if schedOnceStart[i] == currentTime:
				if schedOnceStatus[i] == 1:
					GPIO.output(outletPin[i], GPIO.LOW)
				else:
					GPIO.output(outletPin[i], GPIO.HIGH)
			elif schedOnceEnd[i] == currentTime:
				if schedOnceStatus[i] == 1:
					GPIO.output(outletPin[i], GPIO.HIGH)
				else:
					GPIO.output(outletPin[i], GPIO.LOW)
				schedOnceOngoing[i] = 0

	f = open('schedule.txt')
	line = f.readline()

	while line:
		outlet = int(line[0])
		status = int(line[2])
		startTime = line[4] + line[5] + line[6] + line[7] + line[8]
		endTime = line[10] + line[11] + line[12] + line[13] + line[14]
		startDay = line[16]
		endDay = line[17]
		if currentTime == startTime:
			if currentDay >= startDay and currentDay <= endDay:
				if durOngoing[outlet] == 0:
					if status == 1:
						GPIO.output(outletPin[outlet], GPIO.LOW)
					else:
						GPIO.output(outletPin[outlet], GPIO.HIGH)
		elif currentTime == endTime:
			if currentDay >= startDay and currentDay <= endDay:
				if durOngoing[outlet] == 0:
					if status == 1:
						GPIO.output(outletPin[outlet], GPIO.HIGH)
					else:
						GPIO.output(outletPin[outlet], GPIO.LOW)

		line = f.readline()
	f.close()


stopFlag = Event()
durThread = durationThread(stopFlag)
durThread.start()
schedThread = scheduleThread(stopFlag)
schedThread.start()

print "ready"
while True:
	r = requests.get(url+timetoken)
	if (r.ok):
		data = json.loads(r.text)
		timetoken = str(data[1])
		print "got timetoken: ", timetoken
		if (len(data[0]) > 0):
			print json.dumps(data[0], indent = 2)
			command = int(data[0][0]['command'])
			outlet = int(data[0][0]['outlet'])

			# command to turn outlet on or off
			if command == 0:
				status = int(data[0][0]['status'])
				if status == 1:
					durOngoing[outlet] = 0
					GPIO.output(outletPin[outlet], GPIO.LOW)
				elif status == 0:
					durOngoing[outlet] = 0
					GPIO.output(outletPin[outlet], GPIO.HIGH)
				durOngoing[outlet] = 0

			# command to turn outlet on or off for some duration
			elif command == 1:
				status = int(data[0][0]['status'])
				duration = list(data[0][0]['duration'])
				seconds = 0
				numDur = 0
				flag = 0
				for i in range (0, len(duration)):
					letter = duration[i]
					if letter >= '0' and letter <= '9':
						numDur = numDur * 10 + int(duration[i])
					elif letter == 'T':
						flag = 1
					elif flag == 0 and letter == 'Y':
                                		seconds += numDur * 31536000
						numDur = 0
					elif flag == 0 and letter == 'M':
						seconds += numDur * 2592000
						numDur = 0
					elif flag == 0 and letter == 'D':
						seconds += numDur * 86400
						numDur = 0
					elif flag == 1 and letter == 'H':
						seconds += numDur * 3600
						numDur = 0
					elif flag == 1 and letter == 'M':
						seconds += numDur * 60
						numDur = 0
					elif flag == 1 and letter == 'S':
						seconds += numDur
						numDur = 0

				print "duration (sec):", seconds
				durOngoing[outlet] = 1
				durStatus[outlet] = status
				durSeconds[outlet] = seconds
				if status == 1:
					GPIO.output(outletPin[outlet], GPIO.LOW)
				else:
					GPIO.output(outletPin[outlet], GPIO.HIGH)
				
			# command to turn outlet on or off from some time to some time
			elif command == 2:
				status = int(data[0][0]['status'])
				startTime = data[0][0]['startTime']
				endTime = data[0][0]['endTime']
				schedule = int(data[0][0]['schedule'])

				if schedule == 0:
					schedOnceOngoing[outlet] = 1
					schedOnceStatus[outlet] = status
					schedOnceStart[outlet] = startTime
					schedOnceEnd[outlet] = endTime
				else:
					f = open('schedule.txt', 'a')
					f.write(str(outlet)+' '+str(status)+' '+startTime+' '+endTime+' '+str(schedule)+'\n')
					f.close()
			
			elif command == 4:
				f = open('schedule.txt')
				t = open('temp.txt', 'w')
				line = f.readline()
				while line:
					print line
					if int(line[0]) != outlet:
						t.write(line)
					line = f.readline()
				f.close()
				t.close()
				f = open('schedule.txt', 'w')
				t = open('temp.txt')
				line = t.readline()
				while line:
					print line
					f.write(line)
					line = t.readline()
				f.close()
				t.close()


	else:
		print "HTTP GET error:", r.status_code
		exit(0)
