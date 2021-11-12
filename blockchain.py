from time import time, sleep
from plotter import Plotter

import hashlib
import random
import typing
import threading
import queue


def genMerkelRoot():
    return int(''.join(random.choices('0123456789abcdef', k=4)), 16)


class BlockHeader():

    def __init__(self, prevBlockHash: int, merkelRoot: int, timestamp: int):
        self.prevBlockHash = prevBlockHash
        self.merkelRoot = merkelRoot
        self.timestamp = timestamp

    def __str__(self):
        return ':'.join([str(self.prevBlockHash), str(self.merkelRoot), str(self.timestamp)])

    @classmethod
    def generate(cls, rawStr):
        s1, s2, s3 = rawStr.split(':')
        return cls(int(s1), int(s2), int(s3))


class BlockBody():

    def __init__(self, data: str = ''):
        self.data = data

    def __str__(self):
        return self.data

    @classmethod
    def generate(cls, rawStr):
        return cls(rawStr)


class Block():
    def __init__(self, blockHeader: BlockHeader, blockBody: BlockBody, isGenesis=False, isMine=False):
        self.blockHeader = blockHeader
        self.blockBody = blockBody
        self.isGenesis = isGenesis
        self.height = 0
        self.isMine = isMine
        self.children = set()

    def __str__(self):
        return '|'.join([str(self.blockHeader), str(self.blockBody)])

    def hash(self):
        if self.isGenesis:
            return 0x9e1c
        h = hashlib.sha3_256(str(self).encode())
        return int(h.hexdigest()[-4:], 16)

    def addChild(self, block):
        self.children.add(block.hash())

    def getChildrenHashes(self):
        return list(self.children)

    @classmethod
    def generate(cls, rawStr):
        s1, s2 = rawStr.split('|')
        blockHeader = BlockHeader.generate(s1)
        blockBody = BlockBody.generate(s2)
        return cls(blockHeader, blockBody)


class Blockchain():
    def __init__(self):
        self.blocks: typing.Dict[int, Block] = {}
        b = Block(BlockHeader(0, 0, 0), BlockBody(), isGenesis=True)
        self.blocks[b.hash()] = b
        self.latestBlock = b
        self.genesisBlock = b
        self.isReady = threading.Event()
        self.plotBlockchain = False

    def addBlock(self, b: Block):
        self.blocks[b.hash()] = b
        parentBlock = self.blocks[b.blockHeader.prevBlockHash]
        b.height = parentBlock.height + 1
        parentBlock.addChild(b)
        if b.height > self.latestBlock.height:
            self.latestBlock = b

        if self.plotBlockchain:
            self.plotter.addEdge(parentBlock.hash(), b.hash())
            self.plotter.plot()

    def validate(self, b: Block):
        return self.validateBlock(b) and self.validateTimestamp(b)

    def validateBlock(self, b: Block):
        sleep(0.1)
        return (b.hash() not in self.blocks) \
            and (b.blockHeader.prevBlockHash in self.blocks)

    def validateTimestamp(self, b: Block):
        t = int(time())
        return t-3600 <= b.blockHeader.timestamp <= t+3600

    def height(self):
        return self.latestBlock.height

    def prevHash(self):
        return self.latestBlock.hash()

    def getBlocks(self, n) -> typing.List[Block]:
        '''Yields all blocks with height <= n'''
        q = queue.Queue(0)
        q.put(self.genesisBlock)

        while not q.empty():
            b: Block = q.get()
            if b.height > n:
                continue
            yield b
            for h in b.getChildrenHashes():
                q.put(self.blocks[h])

    def getLongestChain(self) -> typing.List[Block]:
        b = self.latestBlock
        while not b.isGenesis:
            yield b
            b = self.blocks[b.blockHeader.prevBlockHash]

    def addOldBlockStr(self, blockStr):
        b = Block.generate(blockStr)
        if self.validateBlock(b):
            self.addBlock(b)
            return b

    def addNewBlockStr(self, blockStr):
        b = Block.generate(blockStr)
        if self.validate(b):
            self.addBlock(b)
            return b

    def addPlotter(self, plotter: Plotter):
        self.plotter = plotter
        self.plotter.addNode(self.genesisBlock.hash())
        self.plotBlockchain = True
