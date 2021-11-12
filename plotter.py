import networkx as nx
import matplotlib.pyplot as plt
import threading


class Plotter:
    def __init__(self, filename):
        self.filename = filename
        self.G = nx.Graph()
        self.redNodes = []
        self.lock = threading.Lock()

    def addNode(self, a):
        with self.lock:
            self.redNodes.append(a)

    def addEdge(self, a, b):
        with self.lock:
            self.G.add_edge(a, b)

    def plot(self):
        with self.lock:
            plt.figure(self.filename, figsize=(25, 15))
            plt.clf()
            pos = nx.spiral_layout(self.G)
            nx.draw_networkx_nodes(self.G, pos)
            nx.draw_networkx_nodes(
                self.G, pos, nodelist=self.redNodes, node_color='red')
            nx.draw_networkx_edges(self.G, pos)
            plt.savefig(self.filename)
