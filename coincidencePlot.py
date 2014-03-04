import numpy as np
from matplotlib.widgets import Button
import sys
import serial
import struct
import array
from bitstring import BitArray
import matplotlib.pyplot as plt
import time



plt.ion()
fig = plt.figure()
axes = fig.add_subplot(111)
axes.set_autoscale_on(True)
axes.autoscale_view(True,True,True)

dataset = (1,1,1,1,1,1,1,1)

index = np.arange(8)
bar_width = 0.3

rects = axes.bar(index,dataset,bar_width)
plt.xticks(index + bar_width/2.0, ("A", "B", "A'", "B'", "C4", "C5", "C6", "C7"))


s = serial.Serial("COM1",19200,bytesize=serial.SEVENBITS,stopbits=serial.STOPBITS_ONE)
buffer = []
count = 0
alldata = np.zeros([8,10])
while True:
    index = count%10
    count += 1
    print "index = ", index
    try:
        data = s.read()
        if data == "\x7f":
            bits = BitArray(bytes=buffer)
	    # test length:
	    if bits.length == 8*40:
		time.sleep(0.1)
            	a, b, c, d, c4, c5, c6, c7 = bits.unpack('uintle:40,uintle:40,uintle:40,uintle:40,uintle:40,uintle:40,uintle:40,uintle:40')
		#print a, b, c, d, c4, c5, c6, c7
                newdata = np.array((a, b, c, d, c4, c5, c6, c7))
		alldata[:,index] = newdata
		if index == 0:
		    print alldata
		    # update plot every 10 shots
		    for rect, h in zip(rects, alldata.mean(axis=1)):
                        rect.set_height(h)

                    axes.relim()
                    axes.autoscale_view(True,True,True)
                    plt.pause(0.001)
                    plt.draw()
            else:
                print "short packet"

            buffer = []
        else:
            buffer.append(data)
    except KeyboardInterrupt:
        print "W: interrupt received, ending data collection"
        break

s.close()



