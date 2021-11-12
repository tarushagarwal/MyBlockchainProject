#!/usr/bin/env python3

import socket
import threading
import argparse
import json
import datetime

MAX_BACKLOG = 5
RECV_BUFFER = 1024
host = None
port = None
peerList = set()

socketBuffers = {}

delim = '<>'

# Return current timestamp


def timestamp():
    return str(datetime.datetime.now()).replace(':', '.')

# Write the received message in outputfile.txt


def programOutput(mssg):
    global host, port
    filename = f'seed_{host}_{port}.log'
    # filename = 'outputfile.txt'
    f = open(filename, 'a')
    print(mssg)
    f.write(mssg+'\n')
    f.close()

# Adding argument parser for taking host/ip and port as command line input


def getParser():
    parser = argparse.ArgumentParser()

    parser.add_argument('host', help='hostname or ip address')
    parser.add_argument('port', help='port', type=int)

    return parser

# Create new socket with default address and default socket type.
# Reusing the socket when it's in TIME_WAIT STATE from previous execution


def getRawSocket():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    return s


buffer = ''


def recv(c):
    '''Decoding the recieved buffer'''
    try:
        while not delim in socketBuffers.setdefault(c, ''):
            newData = c.recv(RECV_BUFFER).decode()
            if newData:
                socketBuffers[c] += newData
            else:
                return ''
        data, socketBuffers[c] = socketBuffers[c].split(delim, 1)
        print(data)
        return data
    except:
        return ''

# Acquiring the lock before sending the encoded data
# Finally releasing the lock corresponding to host:port


def send(c, data):
    try:
        c.sendall(f'{data}{delim}'.encode())
    except:
        pass

# Add the new peer connected to peerList
# If the recieved message from the peer is DeadNode message
# remove it from the peerList


def handlePeer(c: socket.socket):
    host, port = recv(c).split(':')
    programOutput(f'New Connection {host}:{port}')
    send(c, json.dumps(list(peerList)))
    peerList.add((host, port))

    while True:
        data = recv(c)
        if not data:
            c.close()
            break
        cmd, *args = data.split(':')

        # Dead Node:<DeadNode.IP>:<self.timestamp>:<self.IP>
        if cmd == 'Dead Node':
            programOutput("Receiving Dead Node message")
            programOutput(data)
            peerList.discard(tuple(args[:2]))


def main(args):
    '''
    - Creating sockets and binding it with host/ip and port
    - Acced a connection and start a thread to handle handlePeer() method for this connection
    '''
    global host, port
    s = getRawSocket()
    s.bind((args.host, args.port))
    s.listen(MAX_BACKLOG)
    host = args.host
    port = args.port
    while True:
        c, a = s.accept()
        threading.Thread(target=handlePeer, args=(c,)).start()


if __name__ == "__main__":
    args = getParser().parse_args()
    main(args)
