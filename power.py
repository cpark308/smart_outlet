import Adafruit_BBIO.ADC as ADC
import time
from threading import Timer, Thread, Event
from datetime import datetime
from pytz import timezone


Vdivide = 0.00151286
shunt = 1

Vpin = ["AIN0","AIN2"]
Ipin = ["AIN1","AIN3"]

logFile = "power.txt"

Varray = []
Iarray = []
Energy = 0

class powerThread(Thread):
    def __init__(self,event):
        Thread.__init__(self)
        self.stopped = event
    def run(self):
        while not self.stopped.wait(1):
            powerMeasure()

class storeThread(Thread):
    def __init__(self,event):
        Thread.__init__(self)
        self.stopped = event
    def run(self):
        while not self.stopped.wait(60):
            storePower()

def powerMeasure():
    Active = 0
    Vavg = 0
    Iavg = 0

    global Varray
    global Iarray
    global Energy

    index = 0
    if len(Varray) > len(Iarray):
        index = len(Iarray)
    else:
        index = len(Varray)
    print 'i:' + str(index)
    for i in range (0, index):
        Active += Varray[i] * Iarray[i]
        Vavg += Varray[i]
        Iavg += Iarray[i]

    if index:
        Active = Active / index
        Vavg = Vavg / index
        Iavg = Iavg / index
    print 'Active:' + str(Active)
    print 'V:' + str(Vavg)
    print 'I:' + str(Iavg)

    Energy += Active
    Varray = []
    Iarray = []

def storePower():
    central = timezone('US/Central')
    currentDateTime = datetime.now(central)
    currentDate = ""
    if currentDateTime.date().month < 10:
        currentDate = "0" + str(currentDateTime.date().month) + "/"
    else:
        currentDate = str(currentDateTime.date().month) + "/"
    if currentDateTime.date().day < 10:
        currentDate += "0" + str(currentDateTime.date().day) + "/"
    else:
        currentDate += str(currentDateTime.date().day) + "/"
    currentDate += str(currentDateTime.date().year)

    currentTime = str(currentDateTime.time().hour) + ":"
    if currentDateTime.time().minute < 10:
        currentTime += "0" + str(currentDateTime.time().minute)
    else:
        currentTime += str(currentDateTime.time().minute)

    global Energy
    f = open(logFile, 'a')
    f.write(currentDate + ' ' + currentTime + ' ' + str(Energy / 3600) + ' W*hr\n')
    f.close()

    print currentDate + ' ' + currentTime + ' ' + str(Energy / 3600) + ' W*hr'

    Energy = 0

stopFlag = Event()
pwrThread = powerThread(stopFlag)
pwrThread.start()
strThread = storeThread(stopFlag)
strThread.start()

ADC.setup()

while True:
    Varray.append(((ADC.read_raw(Vpin[0]) - ADC.read_raw(Vpin[1])) * 0.000439453125 / Vdivide))
    Iarray.append(((ADC.read_raw(Ipin[0]) - ADC.read_raw(Ipin[1])) * 0.000439453125 / shunt))
    time.sleep(.0002)

