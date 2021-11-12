# Assignment 2

## Setup
```
pip3 install networkx
```
Add your seeds to config.txt

## Running seeds
For all entries in config.txt (say, 127.0.0.1:5000, 127.0.0.1:5001), run
```
./seed.py 127.0.0.1 5000
./seed.py 127.0.0.1 5001
```
in different terminals

## Running peers
```
usage: peer.py [-h] [-p] [--anode ANODE] host port hashpower

positional arguments:
  host           hostname or ip address
  port           port
  hashpower      hashing power of node in percentage

optional arguments:
  -h, --help     show this help message and exit
  -p, --plot     plot the blockchain
  --anode ANODE  node to attack (host:port)
```

```
./peer.py <your ip> <your port> <hashing power>
```
Ex.
```
./peer.py 127.0.0.1 8000 33
```
P.S. You can run as many peers as you like :)

For attack on 127.0.0.1:8000,
```
./peer.py 127.0.0.1 8001 33 --anode 127.0.0.1:8000
```
For visualising blockchain,
```
./peer.py 127.0.0.1 8000 33 -p
```
Blockchain will be plotted in .png file

For arranging the log files in a folder,
```
./manageLogs.py
```

## Attack
For attacking for 10 mins, run each in different terminals
```
taskset -c 0 timeout 600 ./peer.py 127.0.0.1 8000 10 
taskset -c 1 timeout 600 ./peer.py 127.0.0.1 8001 57 -p
taskset -c 2 timeout 600 ./peer.py 127.0.0.1 8002 33 --anode 127.0.0.1:8000
```

## Code description

Multithreaded architecture is used for peer to peer network. Sending queue is maintained which is responsible for sending with 1 second delay (simulating network delay). For each socket, receiver queue is maintained which splits the received data by delimiter and returns the data when called recv function.

Every peer has a blockchain datastructure local to it. The hashing power of a peer is set by cmd args. When a peer is run, then socket is allocated and the peer starts listening for other peers. Then it reads seed's address from config.txt and connects to them and ask for other peer's addresses. Then it selects atmost 4 peers and connects to them, starts receiver thread for receiving messages and handling thread for processing received messages. Then liveliness thread is started.

Now, for each peer, when it receives a block, then it asks the peer to send blockchain till the height of the block. In between, if any block with greater height is received, then it is added to pending queue. When all old blocks are received, mining thread is started which processes the pending queue.

The mining thread first samples the waiting time from exponential distribution according to hashing power. If no blocks comes from network until waiting time is complete, then new block is generated and broadcasted. Else block from network is validated(takes about 0.1 sec) and adds to blockchain and broadcasted.

The attacker node gets a address as cmd arg to which it sends empty blocks with frequency of 10(equal to validation time).

The blockchain blocks consists of Block Header which has prevblockhash, random merkel root and timestamp. The blockBody has the ipaddress:port of the creator of the block(just to see who created the block while logging).

The plotter class is created which plots the live blockchain to a file. To enable this for a peer `-p` should be passed as cmd arg.

## Longest chain criteria

Assume we have a longest chain C. 

Suppose a block is received from network and added to blockchain. If the blockchain height is increased, the the chain with the new block is selected as longest chain else the old chain C is taken as longest.

If the waiting timer expires, then new block is generated and added to blockchain. The chain containg this block is taken as longest chain