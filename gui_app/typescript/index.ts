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
var global_model: any;
var global_event_list: Array<JSON> = [];
var global_sigma_instance: SIGMA.Sigma | null = null;

function fillGraphFromModel(graph: GRAPH.DirectedGraph ,model: any) {

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
            graph.addEdge(process_label, file_label, { color: "black", type: 'arrow'});
        }
    }
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


function addProcessesToGraph(graph: GRAPH.DirectedGraph, model: any) {
    for (const process of model.processes) {
        var process_label = `${process.pid}-${process.name}`;
        graph.addNode(process_label, { x: Math.random(), y: Math.random(), size: 10, color: "red", label: process_label });
    }
}

function addFilesToGraph(graph: GRAPH.DirectedGraph, model: any) {
    for (const file of model.files) {
        var file_label = file.path;
        graph.addNode(file_label, { x: Math.random(), y: Math.random(), size: 10, color: "green", label: file_label });
    }
}


function applyEventToGraph(event: any) {

    var graph = global_sigma_instance?.getGraph();

    switch (event.event_type) {
        case "OpenEvent":
            console.log("OpenEvent");
            var process = global_model.processes[event.process];
            var file = global_model.files[event.file];
            var process_label = `${process.pid}-${process.name}`;
            var file_label = file.path;
            graph?.addEdge(process_label, file_label, { color: "blue", type: 'arrow'});
            break;
    }

}

function setGraphToEvent(event_id: number) {

    const graph = global_sigma_instance?.getGraph();
    graph?.clearEdges();

    var id = 0;
    for (const event of global_event_list) {
        applyEventToGraph(event);
        
        if (id == event_id) {
            break;
        }
        id += 1;
    }

    global_sigma_instance?.refresh();
}


function fillWithEvents(global_model:any, event_container: HTMLDivElement) {

    var id = 0;
    for(const event of global_model.events) {

        global_event_list.push(event);
        var event_button = document.createElement("button");
        event_button.innerHTML = event.description;
        event_button.onclick = (staticValue => () => setGraphToEvent(staticValue))(id);
        event_container.appendChild(event_button);

        id += 1;
    }
}


function initSigma() {
    const graph_container = document.getElementById("graph-container");
    if (!graph_container) {
        throw new Error("Graph container not found");
    }

    const graph = new GRAPH.DirectedGraph();
    global_sigma_instance?.kill();
    global_sigma_instance = new SIGMA.Sigma(graph, graph_container);

    return graph;
}


function fillGraphContainer() {

    const graph = initSigma();
    fillGraphFromModel(graph, global_model);

    const event_container = document.getElementById('event-container');
    if (!event_container) {
        throw new Error("Event container not found");
    }

    fillWithEvents(global_model, <HTMLDivElement>event_container)
}

const setup_button = document.getElementById("setup-button");
setup_button?.addEventListener("click", () => fillGraphContainer());

const load_button = document.getElementById("load-button");
load_button?.addEventListener("click", () => getFileContent());








