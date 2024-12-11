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


var global_model_filename: string;
var global_model: JSON;


function createGraph(model: any) {
    const graph = new GRAPH.DirectedGraph();

    for (const file of model.files) {
        var file_label = file.path;
        graph.addNode(file_label, { x: Math.random(), y: Math.random(), size: 10, color: "green", label: file_label });
    }

    for (const process of model.processes) {
        var process_label = `${process.pid}-${process.name}`;
        graph.addNode(process_label, { x: Math.random(), y: Math.random(), size: 10, color: "red", label: process_label });

        for (const open_info of process.open_infos) {
            const file = model.files[open_info.file];
            var file_label = file.path;
            graph.addEdge(process_label, file_label, { color: "black" });
        }
    }

    return graph;
}


function getFileContent() {
    var input = document.createElement('input');
    input.type = 'file';

    input.onchange = e => {

        if (!e.target) {
            return;
        }

        var inputElement = e.target as HTMLInputElement;
        if (!inputElement || !inputElement.files) {
            throw new Error("File input or files not found");
        }

        var file = inputElement.files[0];

        if (!file) {
            throw new Error("File not found");
        }

        global_model_filename = file.name;

        const filename_textbox = document.getElementById("filename");
        if (!filename_textbox) {
            throw new Error("Filename textbox not found");
        }

        filename_textbox.innerHTML = `Current file : ${global_model_filename}`;


        var reader = new FileReader();
        reader.readAsText(file, 'UTF-8');


        reader.onload = readerEvent => {
            var content = readerEvent.target?.result;
            global_model = JSON.parse(content as string);
        }

    }

    input.click();
}


async function fillGraphContainer() {

    const graph_container = document.getElementById("graph-container");
    if (!graph_container) {
        throw new Error("Graph container not found");
    }

    const graph = createGraph(global_model);
    var sigmaInstance = new SIGMA.Sigma(graph, graph_container);

    const textbox = document.getElementById('textbox');
    if (!textbox) {
        throw new Error("Textbox not found");
    }

    sigmaInstance.addListener('clickNode', function (e) {
        const node = e.node;
        textbox.innerHTML += `${node.toString()} clicked</br>`;
    });
}

const setup_button = document.getElementById("setup-button");
setup_button?.addEventListener("click", () => fillGraphContainer());

const load_button = document.getElementById("load-button");
load_button?.addEventListener("click", () => getFileContent());









