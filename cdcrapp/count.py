import os
import sys
import logging
import argparse

from collections import defaultdict

logger = logging.getLogger()

def parse_conll(filename):

    mentions = set()
    clusters =  defaultdict(lambda:[])
    open_clusters = defaultdict(lambda:[])

    with open(filename) as f:

        prevline = None

        for lno, line in enumerate(f, start=1):
            if line.startswith("#"):
                continue

            if prevline != None:
                line = prevline + line
                prevline = None
                print(line)

            bits = line.split("\t")

            if len(bits) < 8:
                prevline = line
                continue

            #print(bits)
            topic = bits[0]
            subtopic = bits[1]
            doc_id = bits[2]
            sent_id = bits[3]
            word_id = bits[4]

            cluster_id = bits[-1]

            for cid in cluster_id.split("|"):

                cid = cid.strip()

                if cid == "-":
                    continue
                if cid.startswith("(") and cid.endswith(")"):
                    logger.debug(f"Found one word mention {cid[1:-1]}")

                    mentions.add((lno,lno))
                    clusters[cid[1:-1]].append((lno,lno))
                
                elif cid.startswith("("):
                    logger.debug(f"Open mention {cid[1:]} (line {lno})")
                    open_clusters[cid[1:]].append(lno)

                elif cid.endswith(")"):
                    logger.debug(f"End mention {cid[:-1]} (line {lno})")
                    try:
                        start = open_clusters[cid[:-1]].pop(-1)
                    except Exception as e:
                        print(line)
                        print(e)
                        raise e
                    
                    mentions.add((start,lno))
                    clusters[cid[1:-1]].append((start,lno))

    return clusters, mentions



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("gp_file", help="Gold parse file")
    ap.add_argument("pred_file", help="Predicted parse file")
    ap.add_argument("-v","--verbose", action="store_true")

    args = ap.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    else:
        logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    gclusters_map, gmentions = parse_conll(args.gp_file)

    pclusters_map, pmentions = parse_conll(args.pred_file)

    gclusters = set([tuple(x) for x in gclusters_map.values()])
    pclusters = set([tuple(x) for x in pclusters_map.values()])


    print(f"Gold mentions: {len(gmentions)}")
    print(f"Predicted mentions: {len(pmentions)}")
    print(f"Gold clusters: {len(gclusters)}")
    print(f"Predicted clusters: {len(pclusters)}")
    print(f"Strictly correct identified mentions {len(gmentions.intersection(pmentions))}")

    fp_mentions = pmentions - gmentions
    fn_mentions = gmentions - pmentions

    #print(f"Correctly identified chains: {len(gclusters.intersection(pclusters))}")

    print(f"{len(fp_mentions)} False Positive Mentions")
    print(f"{len(fn_mentions)} False Negative Mentions")
                
    





if __name__ == "__main__":
    main()