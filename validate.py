import os
from collections import defaultdict
import sys

with open(sys.argv[1], "r") as f:

    opencs = defaultdict(lambda: [])

    for i,line in enumerate(f, start=1):
        if line.startswith("#"):
            continue

        bits = line.split("\t")

        cluster = bits[-1].strip()

        clusters = cluster.split("|")

        for cluster in clusters:

            if cluster.startswith("(") and not cluster.endswith(")"):
                opencs[cluster[1:]].append(i)

            if cluster.endswith(")") and not cluster.startswith("("):

                if len(opencs[cluster[:-1]]) == 0:
                   print(f"Found close of mention {cluster[:-1]} on line {i} with no corresponding open") 
                else:
                    opencs[cluster[:-1]].pop(-1)

    for key,value in opencs.items():
        
        if len(value) > 0:
            
            for lineno in value:
                print(f"Found open mention for cluster {key} with no corresponding close on line {lineno}")
                
