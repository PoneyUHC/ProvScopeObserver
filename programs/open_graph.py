import networkx as nx
import matplotlib.pyplot as plt


O_RDONLY = 0
O_WRONLY = 1
O_RDWR = 2

programs = set()


def parse_open_report(filename: str) -> nx.Graph:

    graph = nx.DiGraph()

    with open(filename, 'r') as fin:
        lines = fin.readlines()[1:]
        lines = list(filter(lambda x: x!="\n", lines))
        i = 0
        while i < len(lines):
            src = lines[i]
            target = lines[i+1]
            mode = lines[i+2]
            flags = int(lines[i+3])

            programs.add(src)

            if flags == O_RDONLY:
                graph.add_edge(target, src)
            elif flags == O_WRONLY:
                graph.add_edge(src, target)
            elif flags == O_RDWR:
                graph.add_edge(src, target)
                graph.add_edge(target, src)

            i += 4

    return graph



graph = parse_open_report("trace_open.txt")
pos = nx.shell_layout(graph)

color_map = ['red' if node in programs else 'blue' for node in graph]

print(graph)
plt.figure(figsize=(6,4))
nx.draw_networkx(graph, pos=pos, node_color=color_map, arrowsize=20)

# Set margins for the axes so that nodes aren't clipped
# ax = plt.gca()
# ax.margins(0.20)
# plt.axis("off")
nx.write_gexf(graph, "graph.gexf")
plt.show()