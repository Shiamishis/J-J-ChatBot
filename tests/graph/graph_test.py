from src.RAG.graph import Graph
import unittest


class TestGraph(unittest.TestCase):

    def test_steiner_tree_present(self):
        nodes = ['A', 'B', 'C', 'D', 'E']
        edges = [('A', 'B'), ('B', 'C'), ('B', 'D'), ('B', 'E')]
        graph = Graph(nodes, edges)

        terminals = ['A', 'C', 'E']
        steiner_tree = graph.find_steiner_tree(terminals)
        print(steiner_tree)
        self.assertIn('A', steiner_tree)
        self.assertIn('B', steiner_tree)
        self.assertIn('C', steiner_tree)
        self.assertIn('E', steiner_tree)
        self.assertNotIn('D', steiner_tree)

    def test_steiner_tree_not_present(self):
        nodes = ['A', 'B', 'C']
        edges = [('A', 'B')]
        graph = Graph(nodes, edges)

        terminals = ['A', 'C']
        steiner_tree = graph.find_steiner_tree(terminals)
        print(steiner_tree)
        self.assertEqual(len(steiner_tree), 0)
