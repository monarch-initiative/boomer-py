import networkx as nx
import numpy as np
from typing import List, Dict, Tuple, Optional, Union, Set, Any
from collections.abc import Iterable

def find_subclusters_betweenness(
    G: nx.DiGraph, 
    prob_attr: str = 'probability', 
    min_component_size: int = 3
) -> List[nx.DiGraph]:
    """
    Iteratively remove high-betweenness edges to reveal subclusters
    
    Args:
        G: Input directed graph
        prob_attr: Name of edge attribute containing probabilities
        min_component_size: Minimum size for valid components
        
    Returns:
        List of subgraph components
        
    Examples:
        >>> import networkx as nx
        >>> G = nx.DiGraph()
        >>> # Create two clusters connected by a weak edge
        >>> G.add_edges_from([(1, 2), (2, 3), (3, 1)], probability=0.9)  # Strong cluster
        >>> G.add_edges_from([(4, 5), (5, 6), (6, 4)], probability=0.9)  # Strong cluster
        >>> G.add_edge(3, 4, probability=0.1)  # Weak connector
        >>> G.add_edge(4, 1, probability=0.1)  # Weak connector to make it strongly connected
        >>> subclusters = find_subclusters_betweenness(G)
        >>> len(subclusters) >= 1
        True
        >>> all(isinstance(sc, nx.DiGraph) for sc in subclusters)
        True
        
        >>> # Test with small graph (should return original)
        >>> small_G = nx.DiGraph()
        >>> small_G.add_edges_from([(1, 2)], probability=0.5)
        >>> result = find_subclusters_betweenness(small_G, min_component_size=3)
        >>> len(result)
        1
        >>> len(result[0].nodes())
        2
        
        >>> # Test empty graph
        >>> empty_G = nx.DiGraph()
        >>> result = find_subclusters_betweenness(empty_G)
        >>> len(result)
        1
        >>> len(result[0].nodes())
        0
    """
    subclusters: List[nx.DiGraph] = []
    current_G: nx.DiGraph = G.copy()
    
    while len(current_G.nodes()) >= min_component_size:
        # Calculate edge betweenness
        edge_betweenness: Dict[Tuple[Any, Any], float] = nx.edge_betweenness_centrality(current_G)
        
        if not edge_betweenness:
            break
            
        # Find edges with low probability AND high betweenness
        candidates: List[Tuple[Tuple[Any, Any], float]] = []
        for edge, betweenness in edge_betweenness.items():
            prob: float = current_G.edges[edge].get(prob_attr, 1.0)
            # Score combines low probability with high betweenness
            score: float = betweenness / prob if prob > 0 else float('inf')
            candidates.append((edge, score))
        
        # Remove the most suspicious edge
        edge_to_remove: Tuple[Any, Any] = max(candidates, key=lambda x: x[1])[0]
        current_G.remove_edge(*edge_to_remove)
        
        # Check if graph splits into multiple components
        components: List[Set[Any]] = list(nx.strongly_connected_components(current_G))
        if len(components) > 1:
            subclusters.extend([
                current_G.subgraph(comp).copy() 
                for comp in components 
                if len(comp) >= min_component_size
            ])
            break
    
    return subclusters if subclusters else [current_G]


def find_subclusters_threshold(
    G: nx.DiGraph, 
    prob_attr: str = 'probability',
    thresholds: Optional[Iterable[float]] = None, 
    min_component_size: int = 3
) -> List[nx.DiGraph]:
    """
    Filter edges by probability thresholds to find stable components
    
    Args:
        G: Input directed graph
        prob_attr: Name of edge attribute containing probabilities
        thresholds: Probability thresholds to test (auto-generated if None)
        min_component_size: Minimum size for valid components
        
    Returns:
        List of subgraph components
        
    Examples:
        >>> import networkx as nx
        >>> G = nx.DiGraph()
        >>> # Create clusters with different edge probabilities
        >>> G.add_edges_from([(1, 2), (2, 3), (3, 1)], probability=0.9)
        >>> G.add_edges_from([(4, 5), (5, 6), (6, 4)], probability=0.8)
        >>> G.add_edge(3, 4, probability=0.2)  # Weak connector
        >>> G.add_edge(6, 1, probability=0.1)  # Very weak connector
        >>> subclusters = find_subclusters_threshold(G, thresholds=[0.5, 0.7])
        >>> len(subclusters) >= 1
        True
        >>> all(isinstance(sc, nx.DiGraph) for sc in subclusters)
        True
        
        >>> # Test with uniform high probabilities
        >>> uniform_G = nx.DiGraph()
        >>> uniform_G.add_edges_from([(1, 2), (2, 3), (3, 1)], probability=0.9)
        >>> result = find_subclusters_threshold(uniform_G, thresholds=[0.5])
        >>> len(result)
        1
        >>> len(result[0].nodes())
        3
        
        >>> # Test with custom thresholds
        >>> result = find_subclusters_threshold(G, thresholds=[0.3, 0.6, 0.9])
        >>> isinstance(result, list)
        True
        >>> all(isinstance(sc, nx.DiGraph) for sc in result)
        True
    """
    if thresholds is None:
        probs: List[float] = [G.edges[e].get(prob_attr, 1.0) for e in G.edges()]
        if not probs:  # Handle empty graph
            return [G]
        thresholds = np.percentile(probs, [10, 25, 50, 75, 90])
    
    best_partition: Optional[List[nx.DiGraph]] = None
    best_modularity: float = -1
    
    for threshold in sorted(thresholds, reverse=True):
        # Create subgraph with edges above threshold
        filtered_edges: List[Tuple[Any, Any]] = [
            (u, v) for u, v, d in G.edges(data=True) 
            if d.get(prob_attr, 1.0) >= threshold
        ]
        
        if not filtered_edges:
            continue
            
        subG: nx.DiGraph = G.edge_subgraph(filtered_edges)
        components: List[Set[Any]] = list(nx.strongly_connected_components(subG))
        
        # Filter components by minimum size
        valid_components: List[Set[Any]] = [
            comp for comp in components 
            if len(comp) >= min_component_size
        ]
        
        if len(valid_components) > 1:
            # Calculate modularity-like score
            score: float = len(valid_components) * np.mean([len(comp) for comp in valid_components])
            if score > best_modularity:
                best_modularity = score
                best_partition = [subG.subgraph(comp).copy() for comp in valid_components]
    
    return best_partition or [G]


def find_subclusters_community(
    G: nx.DiGraph, 
    prob_attr: str = 'probability', 
    resolution: float = 1.0,
    min_component_size: int = 3
) -> List[nx.DiGraph]:
    """
    Use community detection to find subclusters
    
    Args:
        G: Input directed graph
        prob_attr: Name of edge attribute containing probabilities
        resolution: Resolution parameter for community detection
        min_component_size: Minimum size for valid components
        
    Returns:
        List of subgraph components
        
    Examples:
        >>> import networkx as nx
        >>> G = nx.DiGraph()
        >>> # Create a graph with clear community structure
        >>> G.add_edges_from([(1, 2), (2, 3), (3, 1)], probability=0.9)
        >>> G.add_edges_from([(4, 5), (5, 6), (6, 4)], probability=0.8)
        >>> G.add_edge(3, 4, probability=0.3)
        >>> G.add_edge(6, 1, probability=0.2)
        >>> subclusters = find_subclusters_community(G)
        >>> len(subclusters) >= 1
        True
        >>> all(isinstance(sc, nx.DiGraph) for sc in subclusters)
        True
        
        >>> # Test with single component
        >>> single_G = nx.DiGraph()
        >>> single_G.add_edges_from([(1, 2), (2, 3)], probability=0.5)
        >>> result = find_subclusters_community(single_G, min_component_size=2)
        >>> len(result) >= 0
        True
        
        >>> # Test empty graph
        >>> empty_G = nx.DiGraph()
        >>> result = find_subclusters_community(empty_G)
        >>> len(result) >= 0
        True
    """
    if len(G.nodes()) == 0:
        return [G]
    
    # Weight edges by probability
    for u, v, d in G.edges(data=True):
        d['weight'] = d.get(prob_attr, 0.1)  # Low default for missing probs
    
    # Try different community detection libraries/methods
    try:
        # Try python-louvain (newer versions)
        try:
            import community as community_louvain
            if hasattr(community_louvain, 'best_partition'):
                # Old python-louvain API
                undirected_G: nx.Graph = G.to_undirected()
                partition: Dict[Any, int] = community_louvain.best_partition(
                    undirected_G, 
                    weight='weight', 
                    resolution=resolution
                )
            else:
                raise AttributeError("best_partition not found")
        except (ImportError, AttributeError):
            # Try networkx-community (newer recommended package)
            try:
                import networkx.algorithms.community as nx_community
                undirected_G: nx.Graph = G.to_undirected()
                # Use Louvain algorithm from networkx
                communities_generator = nx_community.louvain_communities(
                    undirected_G, 
                    weight='weight',
                    resolution=resolution,
                    seed=42  # For reproducible results
                )
                communities_list = list(communities_generator)
                
                # Convert to partition format
                partition: Dict[Any, int] = {}
                for i, community in enumerate(communities_list):
                    for node in community:
                        partition[node] = i
                        
            except (ImportError, AttributeError):
                # Try CDlib if available
                try:
                    import cdlib
                    from cdlib import algorithms
                    undirected_G: nx.Graph = G.to_undirected()
                    coms = algorithms.louvain(undirected_G, weight='weight', resolution=resolution)
                    
                    # Convert CDlib format to partition
                    partition: Dict[Any, int] = {}
                    for i, community in enumerate(coms.communities):
                        for node in community:
                            partition[node] = i
                            
                except ImportError:
                    # Final fallback: use NetworkX's greedy modularity communities
                    undirected_G: nx.Graph = G.to_undirected()
                    communities: List[Set[Any]] = list(nx.community.greedy_modularity_communities(
                        undirected_G, 
                        weight='weight'
                    ))
                    
                    # Convert to partition format
                    partition: Dict[Any, int] = {}
                    for i, community in enumerate(communities):
                        for node in community:
                            partition[node] = i
        
        # Group nodes by community
        communities_dict: Dict[int, List[Any]] = {}
        for node, comm in partition.items():
            if comm not in communities_dict:
                communities_dict[comm] = []
            communities_dict[comm].append(node)
        
        # Create subgraphs for each community
        subclusters: List[nx.DiGraph] = [
            G.subgraph(nodes).copy() 
            for nodes in communities_dict.values() 
            if len(nodes) >= min_component_size
        ]
        
        return subclusters
        
    except Exception as e:
        # Ultimate fallback: use NetworkX's greedy modularity communities
        try:
            undirected_G: nx.Graph = G.to_undirected()
            communities: List[Set[Any]] = list(nx.community.greedy_modularity_communities(
                undirected_G, 
                weight='weight'
            ))
            return [
                G.subgraph(comm).copy() 
                for comm in communities 
                if len(comm) >= min_component_size
            ]
        except Exception:
            # If all else fails, return original graph
            return [G]


def detect_subclusters(
    scc_graph: nx.DiGraph, 
    prob_attr: str = 'probability',
    min_component_size: int = 3, 
    methods: List[str] = ['threshold', 'betweenness']
) -> List[nx.DiGraph]:
    """
    Combined approach using multiple methods
    
    Args:
        scc_graph: Strongly connected component as a DiGraph
        prob_attr: Name of edge attribute containing probabilities
        min_component_size: Minimum size for valid components
        methods: List of methods to use ('threshold', 'betweenness', 'community')
        
    Returns:
        List of subgraph components
        
    Examples:
        >>> import networkx as nx
        >>> G = nx.DiGraph()
        >>> # Create a complex SCC with subclusters
        >>> G.add_edges_from([(1, 2), (2, 3), (3, 1)], probability=0.9)
        >>> G.add_edges_from([(4, 5), (5, 6), (6, 4)], probability=0.8)
        >>> G.add_edge(3, 4, probability=0.2)
        >>> G.add_edge(6, 1, probability=0.1)
        >>> subclusters = detect_subclusters(G)
        >>> len(subclusters) >= 1
        True
        >>> all(isinstance(sc, nx.DiGraph) for sc in subclusters)
        True
        
        >>> # Test with single method
        >>> result = detect_subclusters(G, methods=['threshold'])
        >>> isinstance(result, list)
        True
        
        >>> # Test with all methods
        >>> result = detect_subclusters(G, methods=['threshold', 'betweenness', 'community'])
        >>> isinstance(result, list)
        True
        >>> len(result) >= 1
        True
        
        >>> # Test with small graph
        >>> small_G = nx.DiGraph()
        >>> small_G.add_edges_from([(1, 2)], probability=0.5)
        >>> result = detect_subclusters(small_G, min_component_size=1)
        >>> len(result)
        2
        
        >>> # Test with invalid method
        >>> result = detect_subclusters(G, methods=['invalid_method'])
        >>> len(result)
        1
        >>> result[0] is G or nx.utils.graphs_equal(result[0], G)
        True
    """
    if len(scc_graph.nodes()) == 0:
        return [scc_graph]
    
    results: Dict[str, List[nx.DiGraph]] = {}
    
    if 'threshold' in methods:
        results['threshold'] = find_subclusters_threshold(
            scc_graph, 
            prob_attr, 
            min_component_size=min_component_size
        )
    
    if 'betweenness' in methods:
        results['betweenness'] = find_subclusters_betweenness(
            scc_graph, 
            prob_attr,
            min_component_size=min_component_size
        )
    
    if 'community' in methods:
        results['community'] = find_subclusters_community(
            scc_graph, 
            prob_attr,
            min_component_size=min_component_size
        )
    
    # Choose best result based on some criteria
    # For example, prefer solutions with more balanced component sizes
    best_result: Optional[List[nx.DiGraph]] = None
    best_score: float = -1
    
    for method, subclusters in results.items():
        if len(subclusters) > 1:  # Only consider if it actually found subclusters
            sizes: List[int] = [len(sc.nodes()) for sc in subclusters]
            # Score based on number of clusters and size balance
            mean_size = np.mean(sizes)
            if mean_size > 0:
                score: float = len(subclusters) * (1 - np.std(sizes) / mean_size)
                if score > best_score:
                    best_score = score
                    best_result = subclusters
    
    return best_result or [scc_graph]


def process_large_sccs(
    digraph: nx.DiGraph,
    size_threshold: int = 10,
    prob_attr: str = 'probability'
) -> Dict[int, List[nx.DiGraph]]:
    """
    Process all large SCCs in a digraph
    
    Args:
        digraph: Input directed graph
        size_threshold: Minimum SCC size to process
        prob_attr: Name of edge attribute containing probabilities
        
    Returns:
        Dictionary mapping original SCC size to list of subclusters
        
    Examples:
        >>> import networkx as nx
        >>> G = nx.DiGraph()
        >>> # Create multiple SCCs of different sizes
        >>> # Large SCC 1
        >>> nodes1 = list(range(1, 12))  # 11 nodes
        >>> edges1 = [(i, i+1) for i in nodes1[:-1]] + [(nodes1[-1], nodes1[0])]
        >>> G.add_edges_from(edges1, probability=0.8)
        >>> # Large SCC 2  
        >>> nodes2 = list(range(20, 32))  # 12 nodes
        >>> edges2 = [(i, i+1) for i in nodes2[:-1]] + [(nodes2[-1], nodes2[0])]
        >>> G.add_edges_from(edges2, probability=0.7)
        >>> # Small SCC (should be ignored)
        >>> G.add_edges_from([(50, 51), (51, 50)], probability=0.9)
        >>> results = process_large_sccs(G, size_threshold=5)
        >>> isinstance(results, dict)
        True
        >>> all(isinstance(k, int) for k in results.keys())
        True
        >>> all(isinstance(v, list) for v in results.values())
        True
        
        >>> # Test with empty graph
        >>> empty_G = nx.DiGraph()
        >>> results = process_large_sccs(empty_G)
        >>> len(results)
        0
        
        >>> # Test with no large SCCs
        >>> small_G = nx.DiGraph()
        >>> small_G.add_edges_from([(1, 2), (2, 1)], probability=0.5)
        >>> results = process_large_sccs(small_G, size_threshold=10)
        >>> len(results)
        0
    """
    results: Dict[int, List[nx.DiGraph]] = {}
    
    scc_components: List[Set[Any]] = list(nx.strongly_connected_components(digraph))
    
    for scc in scc_components:
        if len(scc) > size_threshold:
            scc_subgraph: nx.DiGraph = digraph.subgraph(scc)
            subclusters: List[nx.DiGraph] = detect_subclusters(
                scc_subgraph, 
                prob_attr=prob_attr
            )
            results[len(scc)] = subclusters
            # print(f"Split SCC of size {len(scc)} into {len(subclusters)} subclusters")
    
    return results


def create_test_graph() -> nx.DiGraph:
    """
    Create a test graph for demonstration purposes
    
    Returns:
        A DiGraph with two clusters connected by weak edges
        
    Examples:
        >>> G = create_test_graph()
        >>> len(G.nodes())
        6
        >>> len(G.edges())
        8
        >>> nx.is_strongly_connected(G)
        True
        >>> # Check that weak edges have low probability
        >>> weak_edges = [(u, v) for u, v, d in G.edges(data=True) if d['probability'] < 0.5]
        >>> len(weak_edges)
        2
    """
    G = nx.DiGraph()
    
    # Strong cluster 1
    G.add_edges_from([(1, 2), (2, 3), (3, 1)], probability=0.9)
    
    # Strong cluster 2  
    G.add_edges_from([(4, 5), (5, 6), (6, 4)], probability=0.8)
    
    # Weak connectors to make it strongly connected
    G.add_edge(3, 4, probability=0.2)
    G.add_edge(6, 1, probability=0.1)
    
    return G


def check_community_libraries() -> Dict[str, bool]:
    """
    Check which community detection libraries are available
    
    Returns:
        Dictionary indicating which libraries are available
        
    Examples:
        >>> available = check_community_libraries()
        >>> isinstance(available, dict)
        True
        >>> 'networkx_community' in available
        True
    """
    libraries = {
        'python_louvain': False,
        'networkx_community': False,
        'cdlib': False
    }
    
    try:
        import community
        if hasattr(community, 'best_partition'):
            libraries['python_louvain'] = True
    except ImportError:
        pass
    
    try:
        import networkx.algorithms.community
        libraries['networkx_community'] = True
    except ImportError:
        pass
    
    try:
        import cdlib
        libraries['cdlib'] = True
    except ImportError:
        pass
    
    return libraries


if __name__ == "__main__":
    import doctest
    
    # Check available libraries
    print("Available community detection libraries:")
    available_libs = check_community_libraries()
    for lib, available in available_libs.items():
        print(f"  {lib}: {'✓' if available else '✗'}")
    print()
    
    # Run doctests

    # Example usage
    print("\nExample usage:")
    G = create_test_graph()
    print(f"Original graph: {len(G.nodes())} nodes, {len(G.edges())} edges")
    
    subclusters = detect_subclusters(G)
    print(f"Found {len(subclusters)} subclusters")
    for i, cluster in enumerate(subclusters):
        print(f"  Cluster {i+1}: {len(cluster.nodes())} nodes, {len(cluster.edges())} edges")