
import networkx as nx
from networkx.drawing.nx_agraph import graphviz_layout
import pandas as pd

from ..utils import dict_to_repr

class PSSTNetwork(object):

    def __init__(self, case, prog='sfdp'):
        self._case = case
        self.regenerate_network()
        self.recalculate_positions(prog=prog)

    @property
    def swing_bus(self):
        case = self._case
        swing_bus = case.bus[case.bus['TYPE'] == 3].index[0]
        return swing_bus

    @property
    def positions(self):
        return self._pos

    @positions.setter
    def positions(self, pos):
        self._pos = pos

    @property
    def graph(self):
        return self._G

    @graph.setter
    def graph(self, G):
        self._G = G

    def create_profile_graph(self, y_values):
        self.regenerate_network(load_names=False, gen_names=False)

        swing_bus = self.swing_bus
        bus_distance_matrix_df = pd.DataFrame(nx.shortest_path_length(self.graph))

        pos = dict()
        for k, v in bus_distance_matrix_df.loc[swing_bus].sort_values().to_dict().items():
            pos[k] = (v, y_values[k])

        self.positions = pos

    def __repr__(self):
        d = {'nodes': len(self._G.nodes()),
            'edges': len(self._G.edges())}
        repr_string = dict_to_repr(d)
        return '<{}.{}({})>'.format(self.__class__.__module__,
                                self.__class__.__name__,
                                repr_string)

    def regenerate_network(self, gen_names=None, load_names=None, branch_names=None, bus_names=None):
        case = self._case
        if bus_names is None or bus_names == True:
            bus_names = case.bus_name
        else:
            bus_names = list()
        if gen_names is None or gen_names == True:
            gen_names = case.gen_name
        elif gen_names is False:
            gen_names = list()
        if branch_names is None or branch_names == True:
            branch_names = case.branch_name
        elif branch_names is False:
            branch_names = list()
        if load_names is None or load_names == True:
            load_names = case.load.columns
        elif load_names is False:
            load_names = list()

        G = nx.Graph()

        for bus_name in bus_names:
            bus = case.bus.loc[bus_name].to_dict()
            bus['kind'] = 'bus'
            G.add_node(bus_name, attr_dict=bus)

        for gen_name in gen_names:
            gen = case.gen.loc[gen_name].to_dict()
            gen['kind'] = 'gen'
            G.add_node(gen_name, attr_dict=gen)
            bus_name = gen['GEN_BUS']
            connection = {'kind': 'gen_to_bus'}
            G.add_edge(gen_name, bus_name, attr_dict=connection)

        for branch_name in branch_names:
            branch = case.branch.loc[branch_name].to_dict()
            branch['kind'] = 'branch'
            G.add_edge(branch['F_BUS'], branch['T_BUS'], attr_dict=branch)

        for load_name in load_names:
            G.add_node('Load_' + load_name)
            G.add_edge('Load_' + load_name, load_name, attr_dict={'kind': 'load_to_bus'})

        self._G = G
        self.recalculate_positions()

    def recalculate_positions(self, prog='sfdp', *args, **kwargs):
        self.positions = graphviz_layout(self._G, prog=prog, *args, **kwargs)
        return self.positions

    def draw_buses(self, **kwargs):
        nodelist = kwargs.pop('nodelist', list(self._case.bus.index))
        return self._draw_nodes(nodelist, **kwargs)

    def draw_generators(self, **kwargs):
        nodelist = kwargs.pop('nodelist', list(self._case.gen.index))
        return self._draw_nodes(nodelist, **kwargs)

    def draw_loads(self, **kwargs):
        nodelist = kwargs.pop('nodelist', ['Load_{}'.format(b) for b in self._case.load.columns])
        return self._draw_nodes(nodelist, **kwargs)

    def draw_branches(self, **kwargs):
        edgelist = kwargs.pop('edgelist', [(f, t) for f, t, e in self._G.edges(data=True) if e['kind']=='branch'])
        return self._draw_edges(edgelist, **kwargs)

    def draw_connections(self, connection_kind, **kwargs):
        edgelist = kwargs.pop('edgelist', [(f, t) for f, t, e in self._G.edges(data=True) if e['kind']==connection_kind])
        return self._draw_edges(edgelist, **kwargs)

    def _draw_nodes(self, nodelist, **kwargs):
        node_color = kwargs.get('node_color', 'r')
        if isinstance(node_color, dict):
            node_color = [node_color[n] for n in nodelist]
            kwargs['node_color'] = node_color
        labels = kwargs.get('labels', {k: k for k in nodelist})
        if labels is not False:
            self._draw_node_labels(labels)
        return nx.draw_networkx_nodes(self._G, self._pos, nodelist=nodelist, **kwargs)

    def _draw_node_labels(self, labels, **kwargs):
        pos = kwargs.pop('pos', self._pos)
        return nx.draw_networkx_labels(self._G, pos, labels=labels, **kwargs)

    def _draw_edges(self, edgelist, **kwargs):
        edge_labels = kwargs.get('edge_labels', False)
        if edge_labels is not False:
            if edge_labels is True:
                edge_labels = {(f, t): '({},{})'.format(f, t) for f, t in edgelist}
            self._draw_edge_labels(edge_labels)
        return nx.draw_networkx_edges(self._G, self._pos, edgelist=edgelist, **kwargs)

    def _draw_edge_labels(self, edge_labels, **kwargs):
        pos = kwargs.pop('pos', self._pos)
        return nx.draw_networkx_edge_labels(self._G, pos, edge_labels=edge_labels, **kwargs)

    def draw(self, *args, **kwargs):
        ax = kwargs.get('ax', None)
        if ax is None:
            import matplotlib.pyplot as plt
            fig, axs = plt.subplots(1, 1, figsize=(8, 5))
            ax = axs
            ax.axis('off')
            kwargs['ax'] = ax
        self.draw_loads(*args, **kwargs)
        self.draw_generators(*args, **kwargs)
        self.draw_buses(*args, **kwargs)
        self.draw_branches(*args, **kwargs)
        self.draw_connections('gen_to_bus', *args, **kwargs)
        self.draw_connections('load_to_bus', *args, **kwargs)

    @classmethod
    def _create_network(cls, case, prog='sfdp'):
        return cls(case, prog=prog)


create_network = PSSTNetwork._create_network
