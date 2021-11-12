#!/usr/bin/env python3

from time import sleep, time
from hashlib import sha256
from blockchain import *
from plotter import Plotter

import numpy as np

import os
import socket
import threading
import argparse
import json
import random
import select
import sys
import datetime
import queue
import signal


MAX_BACKLOG = 5
RECV_BUFFER = 1024  # size of receiving buffer
MAX_PEERS_TO_CONNECT = 4  # max number of peer to connect
LIVELINESS_TIMEOUT = 13  # time interval between each liveliness message
LIVELINESS_RETRIES = 3  # max number of retries for liveliness
LATENCY = 1  # time after which message wll be sent

host = None
port = None
seedConns = []  # List of seeds
peerConns = {}  # Dict for peers
sendQueue = queue.Queue(0)
socketQueues = {}

blockchain = Blockchain()
pendingQueue = queue.Queue(0)

interarrivaltime = 3
globalLambda = 1.0/interarrivaltime
localLambda = globalLambda

delim = '<>'
blocksGenerated = 0


def exit_handler(*args):
    blocksIncluded = 0
    for block in blockchain.getLongestChain():
        blocksIncluded += 1 if block.isMine else 0
    output = [
        f'Total blocks : {len(blockchain.blocks)}',
        f'Longest chain blocks : {blockchain.latestBlock.height+1}',
        f'My total blocks : {blocksGenerated}',
        f'My blocks in longest chain : {blocksIncluded}',
    ]
    with open(f'peer_{host}_{port}.summary', 'w') as f:
        for line in output:
            f.write(f'{line}\n')
            print(line)
    os._exit(0)


def programOutput(mssg, console=True):
    '''Write the received message in outputfile.txt'''
    global host, port
    filename = f'peer_{host}_{port}.log'
    # filename = 'outputfile.txt'
    f = open(filename, 'a')
    f.write(mssg+'\n')
    f.close()

    if console:
        print(mssg)


def hash(data):
    '''Encode the data using sha256'''
    return sha256(data.encode()).hexdigest()


def timestamp():
    '''Return current timestamp'''
    return str(datetime.datetime.now()).replace(':', '.')


def getSeeds():
    '''Get list of seed from the config.txt file'''
    seeds = []
    with open('config.txt') as f:
        while True:
            line = f.readline().strip('\n')
            if line == '':
                break
            seeds.append(tuple(line.split(':')))
    return seeds


def getParser():
    '''Adding argument parser for taking host/ip and port as command line input'''
    parser = argparse.ArgumentParser()

    parser.add_argument('host', help='hostname or ip address')
    parser.add_argument('port', help='port', type=int)
    parser.add_argument(
        'hashpower', help='hashing power of node in percentage', type=float)
    parser.add_argument(
        '-p', '--plot', help='plot the blockchain', action='store_true')
    parser.add_argument('--anode', help='node to attack (host:port)')

    return parser


def getRawSocket():
    '''
    Create new socket with default address and default socket type.
    Reusing the socket when it's in TIME_WAIT STATE from previous execution
    '''
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    return s


def startThread(fn, args=(), kwargs=None):
    threading.Thread(target=fn, args=args, kwargs=kwargs).start()


def recvWorker(c):
    buffer = ''
    try:
        while True:
            while not delim in buffer:
                newData = c.recv(RECV_BUFFER).decode()
                if newData:
                    buffer += newData
                else:
                    socketQueues[c].put('')
                    return
            data, buffer = buffer.split(delim, 1)
            socketQueues[c].put(data)
            print(data)
    except Exception as e:
        print(e)


def recv(c):
    '''Decoding the recieved buffer'''
    return socketQueues[c].get()


def sendWorker():
    while True:
        c, data, t = sendQueue.get()
        delay = t - time()
        if delay > 0:
            sleep(delay)
        try:
            c.sendall(f'{data}{delim}'.encode())
        except:
            pass


def send(c, data):
    '''
    Acquiring the lock before sending the encoded data
    Finally releasing the lock corresponding to host:port
    '''
    sendQueue.put((c, data, time() + LATENCY))


def broadcastMessage(data, c):
    '''Broadcast data to all the connected peers, except to peer given by c'''
    for peer, _ in peerConns.values():
        if peer != c:
            send(peer, data)


def sendBlocks(c: socket.socket, height):
    for b in blockchain.getBlocks(height):
        send(c, f'Block:{b.height}:{b}')
    send(c, 'OldBlocksDone')


def handlePeer(c: socket.socket, isNewPeer=False):
    '''
    Handling Peer connections
    - In case of recieving Liveness Reply, marked the respective address as recieved
    - In case of Liveness Request, send the message to all the Peers
    - In case of Gossip Message, marked the message as True if not, and broadcasted it to the network
    '''
    threshholdHeight = -1
    isFirstBlock = True
    while True:
        data = recv(c)
        if not data:
            c.close()
            break
        cmd, *args = data.split(':')

        if cmd == 'Liveness Reply' and tuple(args[3:5]) in peerConns:
            peerConns[tuple(args[3:5])][1] = 0
        elif cmd == 'Liveness Request':
            send(c, ':'.join(['Liveness Reply', *args, host, port]))
        elif cmd == 'Get':
            height = int(args[0])
            startThread(sendBlocks, args=(c, height))
        elif cmd == 'OldBlocksDone':
            if isNewPeer:
                blockchain.isReady.set()
                isNewPeer = False
        elif cmd == 'Block':
            blockHeight = int(args[0])
            if isNewPeer and isFirstBlock:
                threshholdHeight = blockHeight
                send(c, f'Get:{blockHeight}')
                isFirstBlock = False
            blockStr = data.split(':', 2)[2]
            if blockHeight > threshholdHeight:
                pendingQueue.put((blockStr, c))
            else:
                blockchain.addOldBlockStr(blockStr)


def startMining():
    '''
    Method for Mining and Processing received blocks
    - Receives block from pending queue
    - If no block received for duration of waiting time, generates block
    '''
    global blocksGenerated
    programOutput('Started mining')
    prevHash = 0
    waitingTime = 0
    while True:
        prevHash = blockchain.prevHash()
        waitingTime = np.random.exponential(1/localLambda)

        # item has arrived in pending queue
        try:
            blockStr, c = pendingQueue.get(timeout=waitingTime)
            b = blockchain.addNewBlockStr(blockStr)
            if b:
                blockStr = f'Block:{b.height}:{b}'
                programOutput(blockStr, False)
                broadcastMessage(blockStr, c)
            else:
                print("Can't add block to the chain, might be duplicate or attack")

        # timeout occured so generate a block
        except queue.Empty:
            header = BlockHeader(prevHash, genMerkelRoot(), int(time()))
            b = Block(header, BlockBody(f'{host}:{port}'), isMine=True)
            if blockchain.validate(b):
                blocksGenerated += 1
                blockchain.addBlock(b)
                blockStr = f'Block:{b.height}:{b}'
                programOutput(blockStr)
                broadcastMessage(blockStr, None)
            else:
                print("Can't generate block, block with same hash already exists")


def probeLiveliness():
    '''
    Checking Liveliness
    - Check after every LIVELINESS_TIMEOUT, if the number of tries are greater than
    - LIVELINESS_RETIRES then report it as DEADNODE
    - After every LIVELINESS_TIMEOUT, Liveness Request is send
    '''
    def _probeLiveliness():
        for key in list(peerConns):
            try:
                peerConns[key][1] += 1
                if peerConns[key][1] > LIVELINESS_RETRIES:
                    startThread(handleDeadNode, args=(key,))
                    continue
                send(peerConns[key][0],
                     f'Liveness Request:{timestamp()}:{host}:{port}')
            except Exception as e:
                print(e)

    while True:
        startThread(_probeLiveliness)
        sleep(LIVELINESS_TIMEOUT)


def registerWithSeeds(args, seeds):
    '''Connecting to seeds and Getting list of Peers from all the seeds'''
    peers = set()
    for seed in seeds:
        s = getRawSocket()
        try:
            s.connect((seed[0], int(seed[1])))
        except Exception as e:
            programOutput('Cannot connect to seed')
            exit(1)
        send(s, f'{args.host}:{args.port}')
        socketQueues[s] = queue.Queue(0)
        startThread(recvWorker, args=(s,))
        for peer in json.loads(recv(s)):
            peers.add(tuple(peer))

        seedConns.append(s)
    return peers


def startListening(s: socket.socket):
    '''Start a thread of handling handlePeer Method'''
    while True:
        c, _ = s.accept()
        try:
            socketQueues[c] = queue.Queue(0)
            startThread(recvWorker, args=(c,))
            chost, cport = recv(c).split(':')
            peerConns[(chost, cport)] = [c, 0]
            startThread(handlePeer, args=(c,))
            b = blockchain.latestBlock
            send(c, f'Block:{b.height}:{b}')
        except Exception as e:
            print(e)


def connectToPeers(peers):
    '''
    - Creating a socket for each connection with peers
    - Starting the thread to handle the Peers
    '''
    for peer in peers:
        s = getRawSocket()
        try:
            s.connect((peer[0], int(peer[1])))
        except Exception as e:
            print(e)
            exit(0)
        send(s, f'{host}:{port}')
        socketQueues[s] = queue.Queue(0)
        startThread(recvWorker, args=(s,))
        peerConns[peer] = [s, 0]
        startThread(handlePeer, args=(s,), kwargs={'isNewPeer': True})


def handleDeadNode(key):
    '''
    - In case of DeadNode, delete it from peerCons, locks
    - Send messafe to all the connected peers with proper format
    '''
    s, _ = peerConns[key]
    s.close()
    del peerConns[key]

    mssg = f'Dead Node:{key[0]}:{key[1]}:{timestamp()}:{host}:{port}'
    programOutput("Reporting Dead node message")
    programOutput(mssg)
    for c in seedConns:
        send(c, mssg)


def attackNode(c):
    b = Block(BlockHeader(0, 0, 0), BlockBody())
    msg = f'Block:{b.height}:{b}'
    while True:
        send(c, msg)
        sleep(0.1)


def main(args):
    '''
    - Initializing the socket, bind it to host and port.
    - Start a thread to listen to other peers
    - Select (NoOfSeeds/2 + 1) number of random seeds, and connect to
    - MAX_PEERS_TO_CONNECT number of peers at random.
    - Start thread to check liveliness
    '''
    global host, port, localLambda
    host = args.host
    port = str(args.port)
    aNode = tuple(args.anode.split(':')) if args.anode else None
    localLambda = args.hashpower * globalLambda / 100.0
    startThread(sendWorker)

    if args.plot:
        blockchain.addPlotter(Plotter(f'blockchain_{host}_{port}.png'))

    s = getRawSocket()
    s.bind((args.host, args.port))
    s.listen(MAX_BACKLOG)
    startThread(startListening, args=(s,))

    seeds = getSeeds()
    seedSubset = random.sample(seeds, len(seeds) // 2 + 1)
    peers = registerWithSeeds(args, seedSubset)
    programOutput('List of Peers from Seeds: ' + ', '.join(map(str, peers)))

    peers = list(filter(lambda peer: peer != (host, port), peers))
    peerSubset = random.sample(peers, min(len(peers), MAX_PEERS_TO_CONNECT))
    if aNode and aNode not in peerSubset:
        peerSubset.append(aNode)
    connectToPeers(peerSubset)
    if aNode:
        startThread(attackNode, args=(peerConns[aNode][0],))

    startThread(probeLiveliness)
    if len(peerSubset):
        blockchain.isReady.wait()
    startMining()


if __name__ == "__main__":
    args = getParser().parse_args()
    for sigType in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sigType, exit_handler)
    main(args)
