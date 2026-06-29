"""Graph Dataset Processing Service.

Supports:
- Node/Edge data structures
- Graph metrics computation
- Graph visualization export
- Export to NetworkX, GraphML, GML formats
"""
import json
from typing import Dict, Any, Optional, List, Tuple, Set
from uuid import UUID
from datetime import datetime
import structlog
import io

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.data_item import DataItem
from app.core.storage import storage_service

logger = structlog.get_logger()


class GraphNode:
    """Represents a graph node."""
    
    def __init__(
        self, 
        node_id: str, 
        label: str = "", 
        attributes: Dict[str, Any] = None
    ):
        self.id = node_id
        self.label = label
        self.attributes = attributes or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "attributes": self.attributes
        }


class GraphEdge:
    """Represents a graph edge."""
    
    def __init__(
        self,
        source: str,
        target: str,
        weight: float = 1.0,
        label: str = "",
        directed: bool = True,
        attributes: Dict[str, Any] = None
    ):
        self.source = source
        self.target = target
        self.weight = weight
        self.label = label
        self.directed = directed
        self.attributes = attributes or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "weight": self.weight,
            "label": self.label,
            "directed": self.directed,
            "attributes": self.attributes
        }


class Graph:
    """Graph data structure with basic operations."""
    
    def __init__(self, directed: bool = True, name: str = ""):
        self.directed = directed
        self.name = name
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self.metadata: Dict[str, Any] = {}
    
    def add_node(
        self, 
        node_id: str, 
        label: str = "", 
        **attributes
    ) -> GraphNode:
        """Add a node to the graph."""
        node = GraphNode(node_id, label, attributes)
        self.nodes[node_id] = node
        return node
    
    def add_edge(
        self,
        source: str,
        target: str,
        weight: float = 1.0,
        label: str = "",
        **attributes
    ) -> GraphEdge:
        """Add an edge to the graph."""
        # Auto-create nodes if they don't exist
        if source not in self.nodes:
            self.add_node(source)
        if target not in self.nodes:
            self.add_node(target)
        
        edge = GraphEdge(source, target, weight, label, self.directed, attributes)
        self.edges.append(edge)
        return edge
    
    def get_neighbors(self, node_id: str) -> List[str]:
        """Get neighbors of a node."""
        neighbors = []
        for edge in self.edges:
            if edge.source == node_id:
                neighbors.append(edge.target)
            elif not self.directed and edge.target == node_id:
                neighbors.append(edge.source)
        return neighbors
    
    def get_degree(self, node_id: str) -> int:
        """Get degree of a node."""
        degree = 0
        for edge in self.edges:
            if edge.source == node_id or edge.target == node_id:
                degree += 1
        return degree
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert graph to dictionary."""
        return {
            "name": self.name,
            "directed": self.directed,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges],
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Graph":
        """Create graph from dictionary."""
        graph = cls(
            directed=data.get("directed", True),
            name=data.get("name", "")
        )
        graph.metadata = data.get("metadata", {})
        
        for node_data in data.get("nodes", []):
            graph.add_node(
                node_data["id"],
                node_data.get("label", ""),
                **node_data.get("attributes", {})
            )
        
        for edge_data in data.get("edges", []):
            graph.add_edge(
                edge_data["source"],
                edge_data["target"],
                edge_data.get("weight", 1.0),
                edge_data.get("label", ""),
                **edge_data.get("attributes", {})
            )
        
        return graph


class GraphMetrics:
    """Compute graph metrics and statistics."""
    
    def compute_basic_metrics(self, graph: Graph) -> Dict[str, Any]:
        """Compute basic graph metrics."""
        num_nodes = len(graph.nodes)
        num_edges = len(graph.edges)
        
        # Degree statistics
        degrees = [graph.get_degree(n) for n in graph.nodes]
        avg_degree = sum(degrees) / num_nodes if num_nodes > 0 else 0
        max_degree = max(degrees) if degrees else 0
        min_degree = min(degrees) if degrees else 0
        
        # Density
        max_edges = num_nodes * (num_nodes - 1)
        if not graph.directed:
            max_edges = max_edges // 2
        density = num_edges / max_edges if max_edges > 0 else 0
        
        # Find isolated nodes
        isolated = [n for n in graph.nodes if graph.get_degree(n) == 0]
        
        # Find self-loops
        self_loops = sum(1 for e in graph.edges if e.source == e.target)
        
        return {
            "num_nodes": num_nodes,
            "num_edges": num_edges,
            "directed": graph.directed,
            "density": round(density, 4),
            "avg_degree": round(avg_degree, 2),
            "max_degree": max_degree,
            "min_degree": min_degree,
            "isolated_nodes": len(isolated),
            "self_loops": self_loops
        }
    
    def compute_centrality(self, graph: Graph) -> Dict[str, Dict[str, float]]:
        """Compute centrality measures."""
        centrality = {
            "degree": {},
            "betweenness": {},
            "closeness": {}
        }
        
        num_nodes = len(graph.nodes)
        if num_nodes == 0:
            return centrality
        
        # Degree centrality
        for node_id in graph.nodes:
            degree = graph.get_degree(node_id)
            centrality["degree"][node_id] = degree / (num_nodes - 1) if num_nodes > 1 else 0
        
        # Simple betweenness approximation (full algorithm is O(n³))
        # We use a simplified version based on shortest paths
        if num_nodes <= 100:
            centrality["betweenness"] = self._compute_betweenness(graph)
        
        # Closeness centrality (simplified)
        for node_id in graph.nodes:
            neighbors = graph.get_neighbors(node_id)
            if neighbors:
                centrality["closeness"][node_id] = len(neighbors) / (num_nodes - 1)
            else:
                centrality["closeness"][node_id] = 0
        
        return centrality
    
    def _compute_betweenness(self, graph: Graph) -> Dict[str, float]:
        """Compute betweenness centrality (simplified Brandes algorithm)."""
        betweenness = {n: 0.0 for n in graph.nodes}
        
        for source in graph.nodes:
            # BFS to find shortest paths
            distances = {source: 0}
            paths = {source: [[source]]}
            queue = [source]
            
            while queue:
                current = queue.pop(0)
                for neighbor in graph.get_neighbors(current):
                    if neighbor not in distances:
                        distances[neighbor] = distances[current] + 1
                        paths[neighbor] = [p + [neighbor] for p in paths[current]]
                        queue.append(neighbor)
                    elif distances[neighbor] == distances[current] + 1:
                        paths[neighbor].extend([p + [neighbor] for p in paths[current]])
            
            # Count paths through each node
            for target, target_paths in paths.items():
                if target == source:
                    continue
                for path in target_paths:
                    for node in path[1:-1]:  # Exclude source and target
                        betweenness[node] += 1.0 / len(target_paths)
        
        # Normalize
        n = len(graph.nodes)
        norm = (n - 1) * (n - 2) if n > 2 else 1
        
        return {k: round(v / norm, 4) for k, v in betweenness.items()}
    
    def compute_pagerank(
        self, 
        graph: Graph, 
        damping: float = 0.85, 
        iterations: int = 100
    ) -> Dict[str, float]:
        """Compute PageRank for nodes."""
        if not graph.nodes:
            return {}
        
        num_nodes = len(graph.nodes)
        pagerank = {n: 1.0 / num_nodes for n in graph.nodes}
        
        # Build adjacency
        out_degree = {n: 0 for n in graph.nodes}
        incoming = {n: [] for n in graph.nodes}
        
        for edge in graph.edges:
            out_degree[edge.source] = out_degree.get(edge.source, 0) + 1
            if edge.target in incoming:
                incoming[edge.target].append(edge.source)
        
        # Iterate
        for _ in range(iterations):
            new_pr = {}
            for node in graph.nodes:
                rank = (1 - damping) / num_nodes
                for source in incoming.get(node, []):
                    if out_degree.get(source, 0) > 0:
                        rank += damping * pagerank[source] / out_degree[source]
                new_pr[node] = rank
            pagerank = new_pr
        
        return {k: round(v, 6) for k, v in pagerank.items()}
    
    def find_shortest_path(
        self, 
        graph: Graph, 
        start: str, 
        end: str
    ) -> Optional[List[str]]:
        """Find shortest path between two nodes using BFS."""
        if start not in graph.nodes or end not in graph.nodes:
            return None
        
        if start == end:
            return [start]
        
        visited = {start}
        queue = [[start]]
        
        while queue:
            path = queue.pop(0)
            current = path[-1]
            
            for neighbor in graph.get_neighbors(current):
                if neighbor == end:
                    return path + [neighbor]
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])
        
        return None  # No path found
    
    def get_connected_components(self, graph: Graph) -> List[Set[str]]:
        """Find connected components in the graph."""
        if not graph.nodes:
            return []
        
        visited = set()
        components = []
        
        for start in graph.nodes:
            if start in visited:
                continue
            
            # BFS to find component
            component = set()
            queue = [start]
            
            while queue:
                node = queue.pop(0)
                if node in visited:
                    continue
                
                visited.add(node)
                component.add(node)
                
                # Add neighbors (both directions for undirected)
                for edge in graph.edges:
                    if edge.source == node and edge.target not in visited:
                        queue.append(edge.target)
                    if edge.target == node and edge.source not in visited:
                        queue.append(edge.source)
            
            if component:
                components.append(component)
        
        return components
    
    def find_communities(self, graph: Graph) -> List[Set[str]]:
        """Find communities using label propagation (simplified)."""
        if not graph.nodes:
            return []
        
        # Initialize labels
        labels = {n: i for i, n in enumerate(graph.nodes)}
        
        # Iterate until convergence
        changed = True
        max_iterations = 10
        iteration = 0
        
        while changed and iteration < max_iterations:
            changed = False
            iteration += 1
            
            for node in graph.nodes:
                neighbors = graph.get_neighbors(node)
                if not neighbors:
                    continue
                
                # Count neighbor labels
                label_counts = {}
                for neighbor in neighbors:
                    lbl = labels[neighbor]
                    label_counts[lbl] = label_counts.get(lbl, 0) + 1
                
                # Assign most common label
                if label_counts:
                    best_label = max(label_counts, key=label_counts.get)
                    if labels[node] != best_label:
                        labels[node] = best_label
                        changed = True
        
        # Group by labels
        communities = {}
        for node, label in labels.items():
            if label not in communities:
                communities[label] = set()
            communities[label].add(node)
        
        return list(communities.values())


class GraphExporter:
    """Export graphs to various formats."""
    
    def to_graphml(self, graph: Graph) -> str:
        """Export to GraphML format."""
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
            f'  <graph id="{graph.name}" edgedefault="{"directed" if graph.directed else "undirected"}">'
        ]
        
        # Nodes
        for node in graph.nodes.values():
            attrs = ' '.join(f'{k}="{v}"' for k, v in node.attributes.items() if isinstance(v, (str, int, float)))
            lines.append(f'    <node id="{node.id}" {attrs}/>')
        
        # Edges
        for i, edge in enumerate(graph.edges):
            lines.append(f'    <edge id="e{i}" source="{edge.source}" target="{edge.target}"/>')
        
        lines.extend(['  </graph>', '</graphml>'])
        return '\n'.join(lines)
    
    def to_gml(self, graph: Graph) -> str:
        """Export to GML format."""
        lines = [
            'graph [',
            f'  directed {1 if graph.directed else 0}',
            f'  label "{graph.name}"'
        ]
        
        # Create ID mapping
        id_map = {n: i for i, n in enumerate(graph.nodes)}
        
        # Nodes
        for node_id, node in graph.nodes.items():
            lines.extend([
                '  node [',
                f'    id {id_map[node_id]}',
                f'    label "{node.label or node_id}"'
            ])
            for k, v in node.attributes.items():
                if isinstance(v, str):
                    lines.append(f'    {k} "{v}"')
                elif isinstance(v, (int, float)):
                    lines.append(f'    {k} {v}')
            lines.append('  ]')
        
        # Edges
        for edge in graph.edges:
            lines.extend([
                '  edge [',
                f'    source {id_map[edge.source]}',
                f'    target {id_map[edge.target]}',
                f'    weight {edge.weight}'
            ])
            if edge.label:
                lines.append(f'    label "{edge.label}"')
            lines.append('  ]')
        
        lines.append(']')
        return '\n'.join(lines)
    
    def to_networkx_json(self, graph: Graph) -> str:
        """Export to NetworkX JSON format."""
        data = {
            "directed": graph.directed,
            "multigraph": False,
            "graph": {"name": graph.name, **graph.metadata},
            "nodes": [
                {"id": n.id, **n.attributes}
                for n in graph.nodes.values()
            ],
            "links": [
                {
                    "source": e.source,
                    "target": e.target,
                    "weight": e.weight,
                    **e.attributes
                }
                for e in graph.edges
            ]
        }
        return json.dumps(data, indent=2)
    
    def to_cytoscape_json(self, graph: Graph) -> str:
        """Export to Cytoscape.js JSON format (for visualization)."""
        elements = {
            "nodes": [
                {
                    "data": {
                        "id": n.id,
                        "label": n.label or n.id,
                        **n.attributes
                    }
                }
                for n in graph.nodes.values()
            ],
            "edges": [
                {
                    "data": {
                        "id": f"e{i}",
                        "source": e.source,
                        "target": e.target,
                        "weight": e.weight,
                        "label": e.label
                    }
                }
                for i, e in enumerate(graph.edges)
            ]
        }
        return json.dumps(elements, indent=2)


class GraphService:
    """Main service for graph data processing."""
    
    def __init__(self):
        self.metrics = GraphMetrics()
        self.exporter = GraphExporter()
    
    async def create_graph_from_items(
        self,
        db: AsyncSession,
        project_id: UUID,
        node_field: str = "id",
        edge_source_field: str = "source",
        edge_target_field: str = "target"
    ) -> Dict[str, Any]:
        """Create a graph from project items."""
        result = await db.execute(
            select(DataItem).where(DataItem.project_id == project_id)
        )
        items = result.scalars().all()
        
        if not items:
            return {"error": "No items found"}
        
        graph = Graph(name=f"Project_{project_id}")
        
        # Try to build graph from item metadata
        for item in items:
            metadata = item.item_metadata or {}
            
            # Check if item represents a node
            if node_field in metadata:
                node_id = str(metadata[node_field])
                label = metadata.get("label", item.name or "")
                graph.add_node(node_id, label, **{
                    k: v for k, v in metadata.items()
                    if k not in [node_field, "label", edge_source_field, edge_target_field]
                })
            
            # Check if item represents an edge
            if edge_source_field in metadata and edge_target_field in metadata:
                source = str(metadata[edge_source_field])
                target = str(metadata[edge_target_field])
                weight = float(metadata.get("weight", 1.0))
                graph.add_edge(source, target, weight)
        
        # If no graph structure found, create from item relationships
        if not graph.nodes and not graph.edges:
            for item in items:
                graph.add_node(str(item.id), item.name or "")
        
        # Compute metrics
        metrics = self.metrics.compute_basic_metrics(graph)
        
        return {
            "graph": graph.to_dict(),
            "metrics": metrics
        }
    
    async def analyze_graph(
        self,
        db: AsyncSession,
        project_id: UUID
    ) -> Dict[str, Any]:
        """Analyze graph structure and compute metrics."""
        graph_result = await self.create_graph_from_items(db, project_id)
        
        if "error" in graph_result:
            return graph_result
        
        graph = Graph.from_dict(graph_result["graph"])
        
        # Compute all metrics
        basic = self.metrics.compute_basic_metrics(graph)
        centrality = self.metrics.compute_centrality(graph)
        communities = self.metrics.find_communities(graph)
        
        # Find top nodes by centrality
        top_nodes = []
        if centrality.get("degree"):
            sorted_nodes = sorted(
                centrality["degree"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            top_nodes = [{"node": n, "degree_centrality": c} for n, c in sorted_nodes]
        
        return {
            "basic_metrics": basic,
            "centrality": centrality,
            "communities": {
                "count": len(communities),
                "sizes": [len(c) for c in communities]
            },
            "top_nodes": top_nodes
        }
    
    async def export_graph(
        self,
        db: AsyncSession,
        project_id: UUID,
        format: str = "graphml"
    ) -> Dict[str, Any]:
        """Export graph to specified format."""
        graph_result = await self.create_graph_from_items(db, project_id)
        
        if "error" in graph_result:
            return graph_result
        
        graph = Graph.from_dict(graph_result["graph"])
        
        # Export to requested format
        if format == "graphml":
            content = self.exporter.to_graphml(graph)
            ext = "graphml"
            mime = "application/xml"
        elif format == "gml":
            content = self.exporter.to_gml(graph)
            ext = "gml"
            mime = "text/plain"
        elif format == "networkx":
            content = self.exporter.to_networkx_json(graph)
            ext = "json"
            mime = "application/json"
        elif format == "cytoscape":
            content = self.exporter.to_cytoscape_json(graph)
            ext = "json"
            mime = "application/json"
        else:
            return {"error": f"Unsupported format: {format}"}
        
        # Store export
        filename = f"graph_{project_id}.{ext}"
        storage_path = storage_service.upload_file(
            io.BytesIO(content.encode('utf-8')),
            filename,
            mime,
            f"exports/{project_id}"
        )
        
        return {
            "format": format,
            "download_path": storage_path,
            "filename": filename,
            "nodes": len(graph.nodes),
            "edges": len(graph.edges)
        }


# Global instance
graph_service = GraphService()
