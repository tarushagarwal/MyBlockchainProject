#!/usr/bin/env python3

import argparse
import os
import glob

attackPower = input('Attack Power: ')
interarrivalTime = input('Interarrival Time: ')

directory = f'inter_{interarrivalTime}_attack_{attackPower}'

fileTypes = ['*.log', '*.summary', '*.png']

for fileType in fileTypes:
    for file in glob.glob(fileType):
        print(file)
        os.renames(file, f'{directory}/{file}')