from core.consensus_v2 import cluster_strategy_vectors


def test_cluster_strategy_vectors_keeps_shape_for_insufficient_seats():
    result = cluster_strategy_vectors({"doubao": [0.1, 0.2]}, threshold=0.45)

    assert result == {
        "cluster_count": 0,
        "largest_cluster_size": 0,
        "clusters": [],
        "alignment_warnings": [],
        "threshold": 0.45,
    }
