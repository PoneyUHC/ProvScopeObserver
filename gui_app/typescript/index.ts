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


interface EventButton {
    event : JSON;
    button : HTMLButtonElement;
}


var global_model_filename: string;
var global_model: any;
var global_event_button_list: Array<EventButton> = [];
var global_current_event_index = 0;
var global_sigma_instance: SIGMA.Sigma | null = null;

function fillGraphFromModel(graph: GRAPH.DirectedGraph, model: any) {

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

        for (const [i, channel] of model.channels.entries()) {
            var channel_label = channel.name;
    
            if( !graph.hasNode(channel_label) ){
                graph.addNode(channel_label, { x: Math.random(), y: Math.random(), size: 10, color: "blue", label: channel_label });
            }

            for (const comm_info of process.communication_infos) {
                if (comm_info.channel === i) {
                    if ( !graph.hasEdge(process_label, channel_label) ){
                        var edge = graph.addEdge(process_label, channel_label, { size: 3, color: "black", type: 'arrow'});
                        graph.setEdgeAttribute(edge, "definitive", true);
                        graph.setEdgeAttribute(edge, "fd", 1);
                        graph.setEdgeAttribute(edge, "is_opened", true);
                    }
                }
            }
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

function applyEventToGraph(event: any) : () => void {

    var graph = global_sigma_instance?.getGraph();
    var highlightCallback: () => void = () => {};

    switch (event.event_type) {
        case "OpenEvent":
            console.log("OpenEvent");
            var process = global_model.processes[event.process];
            var file = global_model.files[event.file];
            var process_label = `${process.pid}-${process.name}`;
            var file_label = file.path;
            var edge = graph?.addEdge(process_label, file_label, { size: 3, color: "blue", type: 'arrow'});
            graph?.setEdgeAttribute(edge, "fd", event.fd);
            graph?.setEdgeAttribute(edge, "is_opened", true);
            break;

        case "CloseEvent":
            console.log("CloseEvent");
            var process = global_model.processes[event.process];
            var process_label = `${process.pid}-${process.name}`;
            var edge = graph?.findEdge((_, edgeAttribs, source) => source === process_label && edgeAttribs.fd === event.fd && edgeAttribs.is_opened);
            graph?.setEdgeAttribute(edge, "color", "lightgrey");
            graph?.setEdgeAttribute(edge, "is_opened", false);
            break;

        case "ReadEvent":
            console.log("ReadEvent");
            var process = global_model.processes[event.process];
            var process_label = `${process.pid}-${process.name}`;
            var edge = graph?.findEdge((_, edgeAttribs, source) => source === process_label && edgeAttribs.fd === event.fd && edgeAttribs.is_opened);
            highlightCallback = () => graph?.setEdgeAttribute(edge, "color", "green");
            break;

        case "WriteEvent":
            console.log("WriteEvent");
            var process = global_model.processes[event.process];
            var process_label = `${process.pid}-${process.name}`;
            var edge = graph?.findEdge((_, edgeAttribs, source) => source === process_label && edgeAttribs.fd === event.fd && edgeAttribs.is_opened);
            highlightCallback = () => graph?.setEdgeAttribute(edge, "color", "red");
            break;
        
    }

    return highlightCallback

}


function cleanGraph() {
    const graph = global_sigma_instance?.getGraph();
    var edges_to_keep = graph?.filterDirectedEdges((_, edgeAttribs) => edgeAttribs.definitive);

    for (const edge of graph?.edges()! ) {
        if( edges_to_keep?.includes(edge) ) {
            graph?.setEdgeAttribute(edge, "color", "black");
        } else {
            graph?.dropEdge(edge);
        }
    }
}

function setGraphToEvent(event_id: number) {

    if(event_id < 0 || event_id >= global_event_button_list.length) {
        return
    }

    cleanGraph();

    var highlightCallback = () => {};

    var id = 0;
    for (const event_button of global_event_button_list) {
        highlightCallback = applyEventToGraph(event_button.event);
        event_button.button.style.background = 'grey'
        
        if (id == event_id) {
            highlightCallback();
            event_button.button.style.background = 'red'
            break;
        }
        id += 1;
    }

    for (const event_button of global_event_button_list.slice(id+1)) {
        event_button.button.style.background = 'lightgrey'
    }

    global_current_event_index = id;
    global_sigma_instance?.refresh();
}


function fillWithEventButtons(global_model: any, event_container: HTMLDivElement) {

    var id = 0;
    for(const event of global_model.events) {

        let event_button: EventButton = {event: event, button: document.createElement("button")};
        global_event_button_list.push(event_button);

        let button = event_button.button
        button.innerHTML = event.description;
        button.onclick = (staticValue => () => setGraphToEvent(staticValue))(id);
        event_container.appendChild(button);

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

    setupDragDrop(global_sigma_instance, graph);

    return graph;
}


function fillGraphContainer() {

    const graph = initSigma();
    fillGraphFromModel(graph, global_model);

    const event_container = document.getElementById('event-container');
    if (!event_container) {
        throw new Error("Event container not found");
    }

    fillWithEventButtons(global_model, <HTMLDivElement>event_container)
}


function setupDragDrop(renderer: SIGMA.Sigma, graph: GRAPH.DirectedGraph) {
    
    let draggedNode: string | null = null;
    let isDragging = false;

    // On mouse down on a node
    //  - we enable the drag mode
    //  - save in the dragged node in the state
    //  - highlight the node
    //  - disable the camera so its state is not updated
    renderer.on("downNode", (e) => {
    isDragging = true;
    draggedNode = e.node;
    graph.setNodeAttribute(draggedNode, "highlighted", true);
    if (!renderer.getCustomBBox()) renderer.setCustomBBox(renderer.getBBox());
    });

    // On mouse move, if the drag mode is enabled, we change the position of the draggedNode
    renderer.on("moveBody", ({ event }) => {
    if (!isDragging || !draggedNode) return;

    // Get new position of node
    const pos = renderer.viewportToGraph(event);

    graph.setNodeAttribute(draggedNode, "x", pos.x);
    graph.setNodeAttribute(draggedNode, "y", pos.y);

    // Prevent sigma to move camera:
    event.preventSigmaDefault();
    event.original.preventDefault();
    event.original.stopPropagation();
    });

    // On mouse up, we reset the dragging mode
    const handleUp = () => {
    if (draggedNode) {
        graph.removeNodeAttribute(draggedNode, "highlighted");
    }
    isDragging = false;
    draggedNode = null;
    };
    renderer.on("upNode", handleUp);
    renderer.on("upStage", handleUp);
}

const setup_button = document.getElementById("setup-button");
setup_button?.addEventListener("click", () => fillGraphContainer());

const load_button = document.getElementById("load-button");
load_button?.addEventListener("click", () => getFileContent());


document.addEventListener(
    "keydown",
    (event) => {
        const keyName = event.key;

        console.log(keyName);
    
        if(keyName === "ArrowLeft") {
            setGraphToEvent(global_current_event_index - 1)
        }

        if( keyName === "ArrowRight") {
            setGraphToEvent(global_current_event_index + 1)
        }
    },
    false,
);







