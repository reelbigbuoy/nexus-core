# ============================================================================
# Nexus Core
# File: graph_integrity.py
# Description: Shared graph integrity helpers for ID-safe copy/import workflows.
# ============================================================================

import copy
import uuid


def _new_uuid():
    return str(uuid.uuid4())


def _offset_point(value, dx, dy):
    try:
        if hasattr(value, 'x') and hasattr(value, 'y'):
            return (float(value.x()) + dx, float(value.y()) + dy)
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            return (float(value[0]) + dx, float(value[1]) + dy)
    except Exception:
        pass
    return value


def graph_json_safe(value):
    """Return a JSON-safe copy of graph clipboard/save payload fragments.

    Clipboard snapshots can contain nested embedded-subgraph metadata. Some UI
    paths may also leave Qt objects or other non-JSON values in node
    properties. Copy/paste must never fail because one optional property is not
    serializable.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): graph_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [graph_json_safe(v) for v in value]
    if hasattr(value, 'x') and hasattr(value, 'y'):
        try:
            return [float(value.x()), float(value.y())]
        except Exception:
            return str(value)
    try:
        import json
        json.dumps(value)
        return value
    except Exception:
        return str(value)


class GraphIdRewriter:
    """Regenerates graph-local IDs while preserving topology.

    Use this for copy/paste, duplicate, import, and graph merge operations. Do
    not use it for normal file open/load because stable IDs are useful when the
    file itself is the authoritative graph.

    Embedded subgraphs are part of the copied object graph and must be rewritten
    recursively. Linked subgraphs are references to an external authoritative
    file, so the linked path is preserved and the external file is not rewritten.
    """

    @classmethod
    def rewrite_snapshot(cls, snapshot, dx=0.0, dy=0.0):
        snapshot = graph_json_safe(copy.deepcopy(snapshot or {}))
        rewritten, _node_id_map = cls._rewrite_graph_payload(
            snapshot,
            dx=dx,
            dy=dy,
            drop_external_connections=True,
        )
        return rewritten

    @classmethod
    def rewrite_graph_payload(cls, graph_payload):
        """Rewrite a complete graph payload for import/merge workflows.

        Unlike normal file open, import/merge creates a second graph instance in
        an existing workspace. All graph-local node and dynamic-port IDs must be
        fresh, including IDs inside embedded subgraphs.
        """
        graph_payload = graph_json_safe(copy.deepcopy(graph_payload or {}))
        rewritten, _node_id_map = cls._rewrite_graph_payload(
            graph_payload,
            dx=0.0,
            dy=0.0,
            drop_external_connections=False,
        )
        return rewritten

    @classmethod
    def _rewrite_graph_payload(cls, graph_payload, dx=0.0, dy=0.0, drop_external_connections=False):
        graph_payload = copy.deepcopy(graph_payload or {})
        node_id_map = {}
        dynamic_port_id_map = {}
        dynamic_pair_id_map = {}
        new_nodes = []

        for node_entry in graph_payload.get('nodes', []) or []:
            if not isinstance(node_entry, dict):
                continue
            entry = copy.deepcopy(node_entry)
            node_data = entry.get('node_data')
            if not isinstance(node_data, dict):
                node_data = {}
                entry['node_data'] = node_data
            old_node_id = node_data.get('node_id')
            new_node_id = _new_uuid()
            if old_node_id:
                node_id_map[old_node_id] = new_node_id
            node_data['node_id'] = new_node_id

            try:
                node_data['x'] = float(node_data.get('x', 0.0)) + float(dx)
                node_data['y'] = float(node_data.get('y', 0.0)) + float(dy)
            except Exception:
                pass

            properties = node_data.get('properties')
            if isinstance(properties, dict):
                cls._rewrite_dynamic_port_specs(properties, dynamic_port_id_map, dynamic_pair_id_map)
                cls._rewrite_embedded_subgraph_if_present(properties)
            new_nodes.append(entry)

        new_connections = []
        for conn_entry in graph_payload.get('connections', []) or []:
            if not isinstance(conn_entry, dict):
                continue
            source_id = node_id_map.get(conn_entry.get('source_node_id'))
            target_id = node_id_map.get(conn_entry.get('target_node_id'))
            if not source_id or not target_id:
                if drop_external_connections:
                    # Copy/paste only keeps fully internal wires. External partial
                    # wires would otherwise attach to unrelated graph content.
                    continue
                # Import/merge of a complete graph should normally never hit this,
                # but avoid creating half-rewritten connections if the payload is
                # malformed.
                continue
            new_conn = copy.deepcopy(conn_entry)
            new_conn['source_node_id'] = source_id
            new_conn['target_node_id'] = target_id
            new_conn['route_points'] = [
                _offset_point(point, float(dx), float(dy))
                for point in (new_conn.get('route_points') or [])
            ]
            new_connections.append(new_conn)

        graph_payload['nodes'] = new_nodes
        graph_payload['connections'] = new_connections
        return graph_payload, node_id_map

    @classmethod
    def _looks_like_graph_payload(cls, value):
        return isinstance(value, dict) and isinstance(value.get('nodes'), list)

    @classmethod
    def _rewrite_embedded_subgraph_if_present(cls, properties):
        """Rewrite IDs inside an embedded child graph stored on a container node.

        A container in linked mode points at another file. Its linked target is
        not part of the copied graph object and must not be mutated. A container
        in embedded mode owns its child graph, so duplicating/copying the parent
        must duplicate the child graph with fresh node IDs as well.
        """
        mode = str(properties.get('subgraph_source') or properties.get('subgraph_mode') or 'embedded').strip().lower()
        if mode in {'linked', 'file', 'external'}:
            return
        subgraph = properties.get('subgraph')
        if not cls._looks_like_graph_payload(subgraph):
            return
        rewritten_subgraph, _node_id_map = cls._rewrite_graph_payload(
            subgraph,
            dx=0.0,
            dy=0.0,
            drop_external_connections=False,
        )
        properties['subgraph'] = rewritten_subgraph

    @classmethod
    def _rewrite_dynamic_port_specs(cls, properties, port_id_map, pair_id_map):
        specs = properties.get('__dynamic_ports')
        if not isinstance(specs, list):
            return
        for spec in specs:
            if not isinstance(spec, dict):
                continue
            old_id = spec.get('id')
            new_id = _new_uuid()
            if old_id:
                port_id_map[old_id] = new_id
            spec['id'] = new_id
            old_pair_id = spec.get('pair_id') or ''
            if old_pair_id:
                pair_id_map.setdefault(old_pair_id, _new_uuid())
                spec['pair_id'] = pair_id_map[old_pair_id]
