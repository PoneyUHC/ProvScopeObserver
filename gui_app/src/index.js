import * as SIGMA from "sigma";
import * as GRAPH from "graphology";
// Create a graphology graph
const graph = new GRAPH.UndirectedGraph();
graph.addNode("1", { label: "Node 1", x: 0, y: 0, size: 10, color: "blue" });
graph.addNode("2", { label: "Node 2", x: 1, y: 1, size: 20, color: "red" });
graph.addEdge("1", "2", { size: 5, color: "purple" });
const graph_container = document.getElementById("graph-container");
console.log(graph_container);
if (!graph_container) {
    throw new Error("Graph container not found");
}
// Instantiate sigma.js and render the graph
const sigmaInstance = new SIGMA.Sigma(graph, graph_container);
const textbox = document.getElementById('textbox');
if (!textbox) {
    throw new Error("Textbox not found");
}
sigmaInstance.addListener('clickNode', function (e) {
    const node = e.node;
    textbox.innerHTML += `Node ${node.toString()} clicked`;
});
