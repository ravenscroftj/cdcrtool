
import itertools

def muc_score(gt_clusters, pred_clusters):
    """Calculate MUC score - based on number of links between entities
    
    MUC/CONLL co-reference scoring algorithm based on 
    https://www.cs.cmu.edu/~hovy/papers/14ACL-coref-scoring-standard.pdf
    
    """

    R_num = 0
    R_denom = 0

    
    # in the Hovy paper, gt_clusters is 'K'
    for cluster in gt_clusters.values():

        gt_cluster_sigs = set(cluster) #[msig(mention) for mention in cluster]

        R_denom += len(gt_cluster_sigs) -1

        intersecting = 0
        remaining = set(gt_cluster_sigs)
        for pcluster in pred_clusters.values():
            pt_cluster_sigs = set(pcluster) #[msig(mention) for mention in pcluster]


            if len(gt_cluster_sigs.intersection(pt_cluster_sigs)) > 0:
                remaining -= gt_cluster_sigs.intersection(pt_cluster_sigs)
                intersecting += 1

        # mop up singletons and spurious mentions
        intersecting += len(remaining)

        R_num += (len(gt_cluster_sigs) - intersecting)

    P_num = 0
    P_denom = 0


    for pcluster in pred_clusters.values():
        pt_cluster_sigs = set(pcluster) #[msig(mention) for mention in pcluster]

        P_denom += len(pt_cluster_sigs) - 1

        intersecting = 0
        remaining = set(pt_cluster_sigs)
        for cluster in gt_clusters.values():
            gt_cluster_sigs = set(cluster) #[msig(mention) for mention in cluster]

            if len(gt_cluster_sigs.intersection(pt_cluster_sigs)) > 0:
                remaining -= gt_cluster_sigs.intersection(pt_cluster_sigs)
                intersecting += 1
        # mop up singletons and spurious mentions
        intersecting += len(remaining)
        
        print(f"({len(pt_cluster_sigs)}-{intersecting})")
        print(f"{len(pt_cluster_sigs)} - 1")
        P_num += (len(pt_cluster_sigs) - intersecting)

    
    R = R_num / R_denom
    P = P_num / P_denom

    print("recall:", R)
    print("precision:", P)

    if R + P == 0:
        f1 = 0
    else:
        f1 = 2 * R * P / (R+P)

    return R,P,f1


gt_clusters = {
    "K1": ['a','b','c'],
    'K2': ['d','e','f','g'],
}
pred_clusters = {
    "R1": ['a','b'],
    "R2": ['c','d'],
    "R3": ['f','g','h','i']
}


muc_score(gt_clusters, pred_clusters)