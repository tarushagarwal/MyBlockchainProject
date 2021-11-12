#!/usr/bin/env python3

import argparse
import os
import glob
import matplotlib.pyplot as plt

portList = [8000, 8001, 8002]
interarrivalList = range(2,6)

miningList = []
for attack in [0,10,20,30]:
	y_miningPower = []
	for interarrival in interarrivalList:
		avgMiningPower = 0
		for port in portList:
			file = f'logs/inter_{interarrival}_attack_{attack}/peer_127.0.0.1_{port}.summary'
			fObj = open(file)
			lines = fObj.read().split('\n')
			totBlock = int(lines[0].split(':')[1])
			longestChain = int(lines[1].split(':')[1])
			myTotBlocks = int(lines[2].split(':')[1])
			myBlocksInLongestChain = int(lines[3].split(':')[1])

			avgMiningPower += longestChain/totBlock

		avgMiningPower = avgMiningPower/len(portList)
		y_miningPower += [avgMiningPower]
	miningList += [y_miningPower]
print(miningList)

plt.figure(1)
plt.plot(interarrivalList, miningList[0], label = "attack = 0%")
plt.plot(interarrivalList, miningList[1], label = "attack = 10%")
plt.plot(interarrivalList, miningList[2], label = "attack = 20%")
plt.plot(interarrivalList, miningList[3], label = "attack = 30%")
plt.title("Mining power utilization vs interarrival time")
plt.xlabel("interarrival time")
plt.ylabel("Average mining power utilization")
plt.legend()
plt.savefig('Mining power utilization vs interarrival time.png')
plt.show()


fractionList = []
for attack in [0, 10, 20, 30]:
	fList = []
	for interarrival in interarrivalList:
		file = f'logs/inter_{interarrival}_attack_{attack}/peer_127.0.0.1_8002.summary'
		fObj = open(file)
		lines = fObj.read().split('\n')
		longestChain = int(lines[1].split(':')[1])
		myBlocksInLongestChain = int(lines[3].split(':')[1])
		fraction = myBlocksInLongestChain/longestChain
		fList += [fraction]
	fractionList += [fList]
print(fractionList)

plt.figure(2)
plt.plot(interarrivalList, fractionList[0], label="attack = 0%")
plt.plot(interarrivalList, fractionList[1], label="attack = 10%")
plt.plot(interarrivalList, fractionList[2], label="attack = 20%")
plt.plot(interarrivalList, fractionList[3], label="attack = 30%")
plt.title("fraction of main chain blocks vs interarrival time")
plt.xlabel("interarrival time")
plt.ylabel("fraction of main chain blocks")
plt.legend()
plt.savefig('fraction of main chain blocks vs interarrival time.png')
plt.show()

fractionList = []
for attack in [10, 20, 30]:
	fList = []
	for interarrival in interarrivalList:
		file = f'logs/inter_{interarrival}_attack_0/peer_127.0.0.1_8002.summary'
		fObj = open(file)
		lines = fObj.read().split('\n')
		longestChain = int(lines[1].split(':')[1])
		myBlocksInLongestChain = int(lines[3].split(':')[1])
		fraction_0 = myBlocksInLongestChain/longestChain
		file = f'logs/inter_{interarrival}_attack_{attack}/peer_127.0.0.1_8002.summary'
		fObj = open(file)
		lines = fObj.read().split('\n')
		longestChain = int(lines[1].split(':')[1])
		myBlocksInLongestChain = int(lines[3].split(':')[1])
		fraction_1 = myBlocksInLongestChain/longestChain
		fList += [fraction_1/fraction_0]
	fractionList += [fList]
print(fractionList)

plt.figure(3)
plt.plot(interarrivalList, fractionList[0], label="attack = 10%")
plt.plot(interarrivalList, fractionList[1], label="attack = 20%")
plt.plot(interarrivalList, fractionList[2], label="attack = 30%")
plt.title("severity vs interarrival time")
plt.xlabel("interarrival time")
plt.ylabel("severity")
plt.legend()
plt.savefig('severity vs interarrival time.png')
plt.show()