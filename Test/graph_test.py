from src.RAG.graph import Graph
import unittest

class TestGraph(unittest.TestCase):

    def test_steiner_tree_present(self):
        graph = Graph()
        graph.add_node('A')
        graph.add_node('B')
        graph.add_node('C')
        graph.add_node('D')
        graph.add_node('E')
        graph.add_edge('A', 'B')
        graph.add_edge('B', 'C')
        graph.add_edge('B', 'D')
        graph.add_edge('B', 'E')

        terminals = ['A', 'C', 'E']
        steiner_tree = graph.find_steiner_tree(terminals)
        print(steiner_tree)
        self.assertIn('A', steiner_tree)
        self.assertIn('B', steiner_tree)
        self.assertIn('C', steiner_tree)
        self.assertIn('E', steiner_tree)
        self.assertNotIn('D', steiner_tree)
    def test_steiner_tree_not_present(self):
        graph = Graph()
        graph.add_node('A')
        graph.add_node('B')
        graph.add_node('C')
        graph.add_edge('A', 'B')

        terminals = ['A', 'C']
        steiner_tree = graph.find_steiner_tree(terminals)
        print(steiner_tree)
        self.assertEqual(len(steiner_tree), 0)
