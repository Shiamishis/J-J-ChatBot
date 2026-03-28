import networkx as nx
from networkx.algorithms import approximation

class Graph:
    def __init__(self, nodes: list[str] = None, edges: list[tuple[str, str]] = None):
        self.graph = nx.Graph()
        self.graph.add_nodes_from(nodes)
        self.graph.add_edges_from(edges)

    def get_nodes(self):
        return list(self.graph.nodes())

    def get_edges(self):
        return list(self.graph.edges())

    def add_node(self, node):
        self.graph.add_node(node)

    def add_edge(self, node1, node2):
        self.graph.add_edge(node1, node2)

    def get_neighbors(self, node):
        return list(self.graph.neighbors(node))

    def has_node(self, node):
        return self.graph.has_node(node)

    def has_edge(self, node1, node2):
        return self.graph.has_edge(node1, node2)

    def find_steiner_tree(self, terminals):
        """
        Find a Steiner tree connecting the given terminal nodes.
        This is a heuristic approach and may not always yield the optimal solution.
        """
        if not all(self.has_node(t) for t in terminals):
            raise ValueError("All terminal nodes must be in the graph.")

        try:
            steiner_tree = approximation.steiner_tree(self.graph, terminals)
            relevant_nodes = set(steiner_tree.nodes())
            return relevant_nodes
        except Exception as e:
            print(f"Error finding Steiner tree: {e}")
            return []

    def __str__(self):
        return str(self.graph)\

