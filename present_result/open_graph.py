import networkx as nx
import matplotlib.pyplot as plt

from parse_logs.parse_openat import parse_bpf_openat_logs
from ipca_globals import GlobalModel, Process, File, OpenInfo

import json
from json import JSONEncoder

O_RDONLY = 0
O_WRONLY = 1
O_RDWR = 2

class MyEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__

parse_bpf_openat_logs("trace/logs/trace_open.logs")

with open("present_result/output/model.json", "w") as f:
    f.write(json.dumps(GlobalModel, indent=2, cls=MyEncoder))


# graph = parse_bpf_openat_logs("trace/logs/enter.log")
# pos = nx.shell_layout(graph)

# color_map = ['red' if node in programs else 'blue' for node in graph]

# print(graph)
# plt.figure(figsize=(6,4))
# nx.draw_networkx(graph, pos=pos, node_color=color_map, arrowsize=20)

# # Set margins for the axes so that nodes aren't clipped
# # ax = plt.gca()
# # ax.margins(0.20)
# # plt.axis("off")
# nx.write_gexf(graph, "graph.gexf")
# plt.show()