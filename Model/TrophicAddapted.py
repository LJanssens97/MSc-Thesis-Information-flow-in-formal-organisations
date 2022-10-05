import networkx as nx

def trophic_levels(G, weight="weight"):

    import numpy as np

    # find adjacency matrix
    a = nx.adjacency_matrix(G, weight=weight).T.toarray()

    # drop rows/columns where in-degree is zero
    rowsum = np.sum(a, axis=1)
    p = a[rowsum != 0][:, rowsum != 0]
    # normalise so sum of in-degree weights is 1 along each row
    p = p / rowsum[rowsum != 0][:, np.newaxis]

    # calculate trophic levels
    nn = p.shape[0]
    i = np.eye(nn)
    try:
        n = np.linalg.inv(i - p)
    except np.linalg.LinAlgError as err:
        # LinAlgError is raised when there is a non-basal node
        msg = (
            "Trophic levels are only defined for graphs where every "
            + "node has a path from a basal node (basal nodes are nodes "
            + "with no incoming edges)."
        )
        raise nx.NetworkXError(msg) from err
    y = n.sum(axis=1) + 1

    levels = {}

    # all nodes with in-degree zero have trophic level == 1
    zero_node_ids = (node_id for node_id, degree in G.in_degree if degree == 0)
    for node_id in zero_node_ids:
        levels[node_id] = 1

    # all other nodes have levels as calculated
    nonzero_node_ids = (node_id for node_id, degree in G.in_degree if degree != 0)
    for i, node_id in enumerate(nonzero_node_ids):
        levels[node_id] = y[i]

    return levels


def trophic_differences(G, weight="weight"):

    levels = trophic_levels(G, weight=weight)
    diffs = {}
    for u, v in G.edges(data=False):
        diffs[(u, v)] = levels[v] - levels[u]
    return diffs



def trophic_incoherence_parameter(G, weight="weight", cannibalism=False):

    import numpy as np

    if cannibalism:
        diffs = trophic_differences(G, weight=weight)
    else:
        # If no cannibalism, remove self-edges
        self_loops = list(nx.selfloop_edges(G))
        if self_loops:
            # Make a copy so we do not change G's edges in memory
            G_2 = G.copy()
            G_2.remove_edges_from(self_loops)
        else:
            # Avoid copy otherwise
            G_2 = G
        diffs = trophic_differences(G_2, weight=weight)
    return np.std(list(diffs.values()))