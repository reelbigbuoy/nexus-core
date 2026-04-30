# NoDE Lite — Node Development Environment Lite

Node-based visual editor plugin for Nexus.

## Included
- Node graph editing
- Pin-based connections
- Wire routing
- Zoom/pan navigation
- Scene auto-expansion
- View manifests
- Custom node-definition compatibility
- Hierarchical sub-graph containers

## Removed from Lite
- Graph runtime execution
- Debugger controls
- Breakpoints
- Execution inspection panels
- Requirement-specific starter content

## Control-Flow Boundary Nodes
- Every graph layer uses **Flow → Start** and **Flow → End** as its control-flow boundaries.
- A new graph or sub-graph is initialized with one **Start** node and one **End** node.
- **Start** represents graph entry. **End** represents graph exit.
- The default NoDE view limits graphs to one Start and one End node.

## Sub-Graph Containers
- Add **Flow → Sub-Graph Container** to represent a nested graph as a top-level node.
- The container exposes **Exec In** and **Exec Out** ports so normal execution links can attach to the container boundary.
- A wire entering the container **Exec In** maps conceptually to the nested graph's **Start** node.
- The nested graph's **End** node maps conceptually back to the container **Exec Out** port.
- Double-click a sub-graph container, or right-click it and choose **Open Sub-Graph**, to edit the nested graph.
- Right-click a container and choose **Expand Sub-Graph Here** to copy its inner nodes into the current graph and bridge Start/End execution links where possible.
- Legacy saved sub-graphs using Sub-Graph Input / Sub-Graph Output are migrated to Start / End when opened.

### Inline Sub-Graph Expansion
- Sub-Graph Container nodes now show a small **+** button in the top-right corner.
- Clicking **+** expands the nested graph directly into the parent canvas as a temporary visual overlay and hides the original container node while expanded.
- Start and End nodes are hidden in the inline expansion; execution is bridged directly into the first internal node(s) after Start and out from the last internal node(s) before End.
- Expanded subgraph contents are enclosed by a dashed boundary with a **-** button in the top-right corner.
- Clicking **-** collapses the inline expansion, removes the dashed boundary, restores hidden container links, re-shows the original container node, and restores all parent graph nodes to their exact pre-expansion positions.
- Inline expansion does not flatten or permanently copy subgraph nodes into the parent graph model.

### Table Data node

NoDE-Lite includes a **Table Data** node under the Data category. It is a data-only node with no execution ports. Its properties panel provides an editable table and CSV import. When a CSV is imported, the first row is used as column names, each column becomes a dynamic data output port, and each remaining row is stored as table data on the node.

Execution and data connections use separate theme roles (`connection_exec` / `connection_data`, with `wire_exec` / `wire_data` aliases) so wires remain visually distinct across Nexus themes.
