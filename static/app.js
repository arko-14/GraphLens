// ========= Graph & Network Setup =========
let chatHistory = [];
let labelsVisible = true;

fetch('/api/graph/')
    .then(res => res.json())
    .then(data => {
        const container = document.getElementById('mynetwork');

        window.nodesDataset = new vis.DataSet(data.nodes);
        window.edgesDataset = new vis.DataSet(data.edges);

        const networkData = { nodes: window.nodesDataset, edges: window.edgesDataset };

        const options = {
            nodes: {
                shape: 'dot',
                size: 8,
                font: { size: 10, color: '#6b7280', face: 'Inter, sans-serif' },
                borderWidth: 1.5,
                borderWidthSelected: 3,
            },
            edges: {
                width: 1,
                color: { color: '#93c5fd', hover: '#3b82f6', highlight: '#1d4ed8' },
                arrows: { to: { enabled: true, scaleFactor: 0.4 } },
                smooth: { type: 'continuous' },
                font: { size: 0 }  // hide edge labels by default
            },
            physics: {
                stabilization: { iterations: 100 },
                barnesHut: { springLength: 80, springConstant: 0.04, damping: 0.2 }
            },
            groups: {
                Customer:            { color: { background: '#fca5a5', border: '#ef4444' } },
                SalesOrder:          { color: { background: '#93c5fd', border: '#3b82f6' } },
                Product:             { color: { background: '#86efac', border: '#22c55e' } },
                Delivery:            { color: { background: '#d8b4fe', border: '#a855f7' } },
                DeliveryItem:        { color: { background: '#e9d5ff', border: '#a855f7' } },
                BillingDocument:     { color: { background: '#fcd34d', border: '#f59e0b' } },
                BillingDocumentItem: { color: { background: '#fde68a', border: '#f59e0b' } },
                SalesOrderItem:      { color: { background: '#bfdbfe', border: '#3b82f6' } },
                JournalEntry:        { color: { background: '#fda4af', border: '#f43f5e' } },
                Plant:               { color: { background: '#a7f3d0', border: '#10b981' } },
            },
            interaction: { hover: true, tooltipDelay: 200 }
        };

        window.network = new vis.Network(container, networkData, options);

        // Double-click to show entity popup
        window.network.on("doubleClick", function (params) {
            if (params.nodes.length > 0) {
                const nodeId = params.nodes[0];
                const nodeData = window.nodesDataset.get(nodeId);
                if (nodeData && nodeData.group) {
                    fetch(`/api/entities/${nodeData.group}/${nodeId}`)
                        .then(res => res.json())
                        .then(details => showNodePopup(details, nodeData))
                        .catch(() => {});
                }
            } else {
                hideNodePopup();
            }
        });

        window.network.on("click", function(params) {
            if (params.nodes.length === 0) hideNodePopup();
        });
    });

// ========= Fit / Label Controls =========
document.getElementById('fitBtn').addEventListener('click', () => {
    window.network && window.network.fit({ animation: true });
});

document.getElementById('overlayBtn').addEventListener('click', () => {
    labelsVisible = !labelsVisible;
    window.nodesDataset.forEach(n => {
        window.nodesDataset.update({ id: n.id, font: { size: labelsVisible ? 10 : 0 } });
    });
    const btn = document.getElementById('overlayBtn');
    btn.textContent = labelsVisible ? '⊙ Hide Labels' : '⊙ Show Labels';
});

// ========= Node Popup =========
function showNodePopup(details, nodeData) {
    const popup = document.getElementById('nodePopup');
    document.getElementById('nodePopupType').textContent = nodeData.group || 'Node';

    const body = document.getElementById('nodePopupBody');
    body.innerHTML = '';

    const props = details.properties || {};
    const ignore = ['embedding'];
    let count = 0;

    for (const [k, v] of Object.entries(props)) {
        if (ignore.includes(k)) continue;
        if (count >= 12) {
            const more = document.createElement('div');
            more.className = 'node-connections';
            more.textContent = 'Additional fields hidden for readability';
            body.appendChild(more);
            break;
        }
        const row = document.createElement('div');
        row.className = 'node-prop-row';
        row.innerHTML = `<span class="node-prop-key">${k}:</span><span class="node-prop-val">${v ?? ''}</span>`;
        body.appendChild(row);
        count++;
    }

    const rels = (details.relationships || []).filter(r => r.rel_type);
    const connEl = document.createElement('div');
    connEl.className = 'node-connections';
    connEl.textContent = `Connections: ${rels.length}`;
    body.appendChild(connEl);

    popup.classList.add('visible');
}

function hideNodePopup() {
    document.getElementById('nodePopup').classList.remove('visible');
}

document.getElementById('nodePopupClose').addEventListener('click', hideNodePopup);

// ========= Chat Logic =========
function setStatus(text, thinking = false) {
    document.querySelector('.status-text').textContent = text;
    const dot = document.querySelector('.status-dot');
    thinking ? dot.classList.add('thinking') : dot.classList.remove('thinking');
}

function sendMessage() {
    const input = document.getElementById('userInput');
    const msg = input.value.trim();
    if (!msg) return;

    addUserMessage(msg);
    input.value = '';
    input.style.height = 'auto';
    setStatus('Agent is thinking...', true);

    fetch('/api/search/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: msg, history: chatHistory })
    })
    .then(res => res.json())
    .then(data => {
        addAgentMessage(data.answer);
        chatHistory.push({ role: 'user', content: msg });
        chatHistory.push({ role: 'assistant', content: data.answer });
        setStatus('Agent is awaiting instructions', false);

        // Highlight nodes
        try {
            if (data.nodes && data.nodes.length > 0) {
                const validIds = [];
                data.nodes.forEach(n => {
                    if (!window.nodesDataset.get(n.id)) {
                        window.nodesDataset.add({ id: n.id, label: n.label, group: n.group });
                    }
                    validIds.push(n.id);
                });
                if (validIds.length > 0) {
                    window.network.selectNodes(validIds);
                    window.network.focus(validIds[0], { scale: 1.3, animation: true });
                }
            } else {
                window.network.unselectAll();
            }
        } catch(e) { console.warn("Node highlight failed:", e); }
    })
    .catch(() => {
        addAgentMessage("I could not connect to the backend. Please try again.");
        setStatus('Agent is awaiting instructions', false);
    });
}

function addUserMessage(text) {
    const chat = document.getElementById('chatMessages');
    const row = document.createElement('div');
    row.className = 'chat-row user-row';
    row.innerHTML = `
        <div class="user-avatar">You</div>
        <div class="chat-bubble-user">${escapeHtml(text)}</div>
    `;
    chat.appendChild(row);
    chat.scrollTop = chat.scrollHeight;
}

function addAgentMessage(text) {
    const chat = document.getElementById('chatMessages');
    const row = document.createElement('div');
    row.className = 'chat-row agent-row';
    row.innerHTML = `
        <div class="agent-avatar">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="8" r="4" stroke="white" stroke-width="2"/>
                <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" stroke="white" stroke-width="2" stroke-linecap="round"/>
            </svg>
        </div>
        <div class="chat-bubble-agent">
            <div class="agent-name">Graph Agent</div>
            ${marked.parse(text)}
        </div>
    `;
    chat.appendChild(row);
    chat.scrollTop = chat.scrollHeight;
}

function escapeHtml(text) {
    return text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// Auto-resize textarea
document.getElementById('userInput').addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 100) + 'px';
});

document.getElementById('userInput').addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});
