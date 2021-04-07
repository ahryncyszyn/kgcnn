import numpy as np
import scipy.sparse as sp


def precompute_adjacency_scaled(adj_matrix, add_identity=True):
    """
    Precompute the scaled adjacency matrix A_scaled = D^-0.5 (adj_mat + I) D^-0.5.

    Args:
        adj_matrix (np.array,scipy.sparse): Adjacency matrix of shape (N,N).
        add_identity (bool, optional): Whether to add identity. Defaults to True.

    Returns:
        np.array: D^-0.5 (adj_mat + I) D^-0.5.
    """
    if isinstance(adj_matrix, np.ndarray):
        adj_matrix = np.array(adj_matrix, dtype=np.float)
        if add_identity:
            adj_matrix = adj_matrix + np.identity(adj_matrix.shape[0])
        rowsum = np.sum(adj_matrix, axis=-1)
        colsum = np.sum(adj_matrix, axis=0)
        d_ii = np.power(rowsum, -0.5).flatten()
        d_jj = np.power(colsum, -0.5).flatten()
        d_ii[np.isinf(d_ii)] = 0.
        d_jj[np.isinf(d_jj)] = 0.
        di = np.zeros((adj_matrix.shape[0], adj_matrix.shape[0]), dtype=adj_matrix.dtype)
        dj = np.zeros((adj_matrix.shape[1], adj_matrix.shape[1]), dtype=adj_matrix.dtype)
        di[np.arange(adj_matrix.shape[0]), np.arange(adj_matrix.shape[0])] = d_ii
        dj[np.arange(adj_matrix.shape[1]), np.arange(adj_matrix.shape[1])] = d_jj
        return np.matmul(di, np.matmul(adj_matrix, dj))
    elif (isinstance(adj_matrix, sp.bsr.bsr_matrix) or
          isinstance(adj_matrix, sp.csc.csc_matrix) or
          isinstance(adj_matrix, sp.coo.coo_matrix) or
          isinstance(adj_matrix, sp.csr.csr_matrix)):
        adj = sp.coo_matrix(adj_matrix)
        if add_identity:
            adj = adj + sp.eye(adj.shape[0])
        colsum = np.array(adj.sum(0))
        rowsum = np.array(adj.sum(1))
        d_ii = np.power(rowsum, -0.5).flatten()
        d_jj = np.power(colsum, -0.5).flatten()
        d_ii[np.isinf(d_ii)] = 0.
        d_jj[np.isinf(d_jj)] = 0.
        di = sp.diags(d_ii, format='coo')
        dj = sp.diags(d_jj, format='coo')
        return di.dot(adj).dot(dj).tocoo()
    else:
        raise TypeError("Error: Matrix format not supported:", type(adj_matrix))


def convert_scaled_adjacency_to_list(adj_scaled):
    """
    Map adjacency matrix to index list plus edge weights.

    Args:
        adj_scaled (np.array,scipy.sparse): Scaled Adjacency matrix of shape (N,N).
            A_scaled = D^-0.5 (adj_matrix + I) D^-0.5.

    Returns:
        list: [edge_index, edge_weight]
        
        - edge_index (np.array): Indexlist of shape (N,2).
        - edge_weight (np.array): Entries of Adjacency matrix of shape (N,N)
    """
    if isinstance(adj_scaled, np.ndarray):
        a = np.array(adj_scaled > 0, dtype=np.bool)
        edge_weight = adj_scaled[a]
        index1 = np.tile(np.expand_dims(np.arange(0, a.shape[0]), axis=1), (1, a.shape[1]))
        index2 = np.tile(np.expand_dims(np.arange(0, a.shape[1]), axis=0), (a.shape[0], 1))
        index12 = np.concatenate([np.expand_dims(index1, axis=-1), np.expand_dims(index2, axis=-1)], axis=-1)
        edge_index = index12[a]
        return edge_index, edge_weight
    elif (isinstance(adj_scaled, sp.bsr.bsr_matrix) or
          isinstance(adj_scaled, sp.csc.csc_matrix) or
          isinstance(adj_scaled, sp.coo.coo_matrix) or
          isinstance(adj_scaled, sp.csr.csr_matrix)):
        adj_scaled = adj_scaled.tocoo()
        ei1 = np.array(adj_scaled.row.tolist(), dtype=np.int)
        ei2 = np.array(adj_scaled.col.tolist(), dtype=np.int)
        edge_index = np.concatenate([np.expand_dims(ei1, axis=-1), np.expand_dims(ei2, axis=-1)], axis=-1)
        edge_weight = np.array(adj_scaled.data)
        return edge_index, edge_weight
    else:
        raise TypeError("Error: Matrix format not supported:", type(adj_scaled))


def make_adjacency_undirected_logical_or(adj_mat):
    """
    Make adjacency matrix undirected. This adds edges to make adj_matrix symmetric, only if is is not symmetric.
    This is not equivalent to (adj_matrix+adj_matrix^T)/2 but to adj_matrix or adj_matrix^T

    Args:
        adj_mat (np.array,scipy.sparse): Adjacency matrix of shape (N,N)

    Returns:
        np.array, scipy.sparse: Undirected Adjacency matrix. This has adj_matrix=adj_matrix^T.
    """
    if isinstance(adj_mat, np.ndarray):
        at = np.transpose(adj_mat)
        # Aout = np.logical_or(adj_matrix,at)
        a_out = (at > adj_mat) * at + (adj_mat >= at) * adj_mat
        return a_out
    elif (isinstance(adj_mat, sp.bsr.bsr_matrix) or
          isinstance(adj_mat, sp.csc.csc_matrix) or
          isinstance(adj_mat, sp.coo.coo_matrix) or
          isinstance(adj_mat, sp.csr.csr_matrix)):
        adj = sp.coo_matrix(adj_mat)
        adj_t = sp.coo_matrix(adj_mat).transpose()
        a_out = (adj_t > adj).multiply(adj_t) + (adj > adj_t).multiply(adj) + adj - (adj != adj_t).multiply(adj)
        return a_out.tocoo()


def add_self_loops_to_edge_indices(edge_indices, edge_values=None, remove_duplicates=True, sort_indices=True):
    """
    Add self-loops to edge index list, i.e. [[0,0],[1,1]...]. Edge values are filled up with ones.
    Default is to remove duplicates in the entire list. Edge indices are sorted by default.

    Args:
        edge_indices (np.array): Index list of shape (N,2).
        edge_values (np.array): Edge values of shape (N,M) matching the edge_indices
        remove_duplicates (bool): Remove duplicate edge indices. Default is True.
        sort_indices (bool): Sort final edge indices. Default is True.

    Returns:
        edge_indices: Sorted index list with self-loops. Optionally (edge_indices, edge_values).
    """
    clean_edge = None
    max_ind = np.max(edge_indices)
    self_loops = np.arange(max_ind + 1, dtype=np.int)
    self_loops = np.concatenate([np.expand_dims(self_loops, axis=-1), np.expand_dims(self_loops, axis=-1)], axis=-1)
    added_loops = np.concatenate([edge_indices, self_loops], axis=0)
    clean_index = added_loops
    if edge_values is not None:
        edge_loops_shape = [self_loops.shape[0]] + list(edge_values.shape[1:]) if len(edge_values.shape) > 1 else [
            self_loops.shape[0]]
        edge_loops = np.ones(edge_loops_shape)
        clean_edge = np.concatenate([edge_values, edge_loops], axis=0)
    if remove_duplicates:
        un, unis = np.unique(added_loops, return_index=True, axis=0)
        clean_index = added_loops[unis]
        if edge_values is not None:
            clean_edge = clean_edge[unis]
    if sort_indices:
        order1 = np.argsort(clean_index[:, 1], axis=0, kind='mergesort')  # stable!
        ind1 = clean_index[order1]
        if edge_values is not None:
            clean_edge = clean_edge[order1]
        order2 = np.argsort(ind1[:, 0], axis=0, kind='mergesort')
        clean_index = ind1[order2]
        if edge_values is not None:
            clean_edge = clean_edge[order2]
    if edge_values is not None:
        return clean_index, clean_edge
    else:
        return clean_index


def sort_edge_indices(edge_indices, edge_values):
    """
    Sort index list.

    Args:
        edge_indices (np.array): Edge indices of shape (N,2).
        edge_values (np.array): Edge values of shape (N,M).

    Returns:
        list: [ind,val]
        
        - edge_indices (np.array): Sorted indices.
        - edge_values (np.array): Edge values matching sorted indices.
    """
    order1 = np.argsort(edge_indices[:, 1], axis=0, kind='mergesort')  # stable!
    ind1 = edge_indices[order1]
    val1 = edge_values[order1]
    order2 = np.argsort(ind1[:, 0], axis=0, kind='mergesort')
    ind2 = ind1[order2]
    val2 = val1[order2]
    return ind2, val2


def make_edge_indices_symmetric(edge_indices, edge_values):
    pass

def make_adjacency_from_edge_indices():
    pass