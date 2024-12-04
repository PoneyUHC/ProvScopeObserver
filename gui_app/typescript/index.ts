import * as SIGMA from "sigma";
import * as GRAPH from "graphology";

const dummyModel = ` {
  "processes": [
    {
      "pid": 1,
      "name": "process1"
    },
    {
      "pid": 2,
      "name": "process2"
    },
    {
      "pid": 3,
      "name": "process3"
    }
  ]
}`;


function parseModel(model: string): any {
  return JSON.parse(model);
}


function createGraph(model: any) {
  const graph = new GRAPH.UndirectedGraph();

  for (const process of model.processes) {
    graph.addNode(`${process.pid}-${process.name}`, {x:Math.random(), y:Math.random(), size:10, color:"red"});  
  }

  return graph;
}


function fillGraphContainer() {
  const graph_container = document.getElementById("graph-container");
  if (!graph_container) {
    throw new Error("Graph container not found");
  }

  const model = parseModel(dummyModel);

  const graph = createGraph(model);
  var sigmaInstance = new SIGMA.Sigma(graph, graph_container);

  const textbox = document.getElementById('textbox');
  if (!textbox) {
    throw new Error("Textbox not found");
  }

  sigmaInstance.addListener('clickNode', function(e) {
    const node = e.node;
    textbox.innerHTML += `${node.toString()} clicked</br>`;
  });

}

const button = document.getElementById("setup-button");
button?.addEventListener("click", () => fillGraphContainer());









