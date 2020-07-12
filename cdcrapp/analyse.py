"""Error analysis module for coreference model outputs"""

import pickle
import json
import math
import pandas as pd
import streamlit as st 
from collections import defaultdict

FILE_ID_COLUMN = 2
SENT_ID_COLUMN = 3
TOK_ID_COLUMN = 4
TOK_TEXT_COLUMN = 5
CLUSTER_SIGNAL_COLUMN = 7

def parse_conll(file):

    mention_clusters = defaultdict(lambda: [])
    current_mentions = defaultdict(lambda: [])
    document_contents =  defaultdict(lambda: [])
    
    for line in file:
        if line.startswith("#"):
            continue
            
        row = line.split("\t")

        signals = row[CLUSTER_SIGNAL_COLUMN].split("|")

        begins = []
        ends = []

        # append document content to relevant index
        document_contents[row[FILE_ID_COLUMN]].append(row[TOK_TEXT_COLUMN])

        # handle collection of newly starting and ending mentions
        for signal in signals:
            if signal.strip().startswith("("):
                mention_id = signal.strip()[1:]
                if mention_id.endswith(")"):
                    mention_id = mention_id[:-1]
                begins.append(mention_id)

            
            if signal.strip().endswith(")"):
                mention_id = signal.strip()[:-1]
                if mention_id.startswith("("):
                    mention_id = mention_id[1:]
                ends.append(mention_id)


        # append current character to new and existing mentions
        for m_id in begins + list(current_mentions.keys()):
            current_mentions[m_id].append((row[FILE_ID_COLUMN], row[TOK_ID_COLUMN], row[TOK_TEXT_COLUMN]))

        # close out any new mentions that need to be closed out
        for m_id in ends:
            mention_clusters[m_id].append(current_mentions[m_id])
            del current_mentions[m_id]
                
    return mention_clusters, document_contents    

def generate_cluster_table(clusters):
    rows = []
    for cluster_id, cluster in clusters.items():
        #print(cluster)
        if len(cluster[0]) < 1:
            print(cluster_id)
            continue
        for mention in cluster:
            rows.append([cluster_id, mention[0][0], mention[0][1], mention[-1][1], " ".join([tok[2] for tok in mention]) ])

    return pd.DataFrame(rows, columns=['Cluster ID', 'Mention File', 'Mention Start', 'Mention End', 'Mention Text'])

def build_mention_map(clusters):
    mentions = defaultdict(lambda: [])

    for cluster_id, cluster in clusters.items():
        for mention in cluster:
            mention_key = f"{mention[0][0]}_{mention[0][1]}_{mention[-1][1]}"
            mentions[mention_key].append(cluster_id)
    
    return mentions

def analyse_clusters(gt_clusters, pred_clusters):

    gt_mentions = build_mention_map(gt_clusters)
    pred_mentions = build_mention_map(pred_clusters)

    gt_mention_ids = set(gt_mentions.keys())
    pred_mention_ids = set(pred_mentions.keys())

    
    precision = len(gt_mention_ids.intersection(pred_mention_ids)) / len(pred_mention_ids)
    recall = len(gt_mention_ids.intersection(pred_mention_ids)) / len(gt_mention_ids)

    st.markdown(f"## Mention Classification\n\nPrecision: {precision} \n\n Recall: {recall}")


    # take correct mentions
    correct_mentions = gt_mention_ids.intersection(pred_mention_ids)

    correct = 0
    correct_intra = 0
    correct_cross = 0

    total_intra = 0
    total_cross = 0

    for mention in correct_mentions:
        gt_neighbours = gt_clusters[gt_mentions[mention][0]]
        pred_neighbours = pred_clusters[pred_mentions[mention][0]]

        gt_set = set([tuple(mention) for mention in gt_neighbours])
        pr_set = set([tuple(mention) for mention in pred_neighbours])

        doc_keys = [x[0][0] for x in gt_set]

        is_intra = all(x == doc_keys[0] for x in doc_keys)

        if is_intra:
            total_intra += 1
        else:
            total_cross += 1
            
        if gt_set == pr_set: 

            if is_intra:
                correct_intra += 1
            else:
                correct_cross += 1
            
            correct += 1
            print("------------------------------------------------")
            print(gt_neighbours,"\n---\n", pred_neighbours)

    st.markdown(f"## Coreference Resolution")

    st.text(f"Correct co-reference chains: {correct}/{len(correct_mentions )} ({round(correct/len(correct_mentions )*100, 2)}%)")
    st.text(f"Total intra-document chains: {total_intra} Correct intra-document chains: {correct_intra} ({round(correct_intra/total_intra,2)}%)")
    st.text(f"Total cross-document chains: {total_cross} Correct cross-document chains: {correct_cross} ({round(correct_cross/total_cross,2)}%)")


def render_clusters(cluster_ids, clusters, title):
    markdown = f"## {title}\n\n"
    for cluster_id in cluster_ids:
        mentions = []
        markdown += f" - {cluster_id}\n"
        for mention in clusters[cluster_id]:
            print(mention)
            doc = mention[0][0]
            markdown += f"   - {' '.join([word[2] for word in mention])} ({doc})\n" 
    
    st.sidebar.markdown(markdown)
    


def deep_dive(gt_clusters, results_clusters, gt_documents, results_documents):
    """Deep dive on specific documents"""

    doc_ids = list(gt_documents.keys())


    gt_chain_by_doc = defaultdict(lambda: set())

    for cluster_id, cluster in gt_clusters.items():
        for mention in cluster:
            gt_chain_by_doc[mention[0][0]].add(cluster_id)

    pred_chain_by_doc = defaultdict(lambda: set())

    for cluster_id, cluster in results_clusters.items():
        for mention in cluster:
            pred_chain_by_doc[mention[0][0]].add(cluster_id)


    selected_doc = st.sidebar.selectbox("Select document", doc_ids)

    text = gt_documents[selected_doc]

    selected_clusterset = st.sidebar.selectbox("Cluster set", ["Ground Truth","Predicted"])

    if selected_clusterset == "Ground Truth":
        cluster_ids = list(gt_chain_by_doc[selected_doc])
        cluster_collection = gt_clusters
    else:
        cluster_ids = list(pred_chain_by_doc[selected_doc])
        cluster_collection = results_clusters

    selected_clusters = st.sidebar.selectbox("Render clusters", ["All"] + cluster_ids)

    if selected_clusters == "All":
        sel_clusters = {cluster_id: cluster_collection[cluster_id] for cluster_id in cluster_ids}
    else:
        sel_clusters = {selected_clusters: cluster_collection[selected_clusters]}

    render_doc(selected_doc, text, sel_clusters)

    #st.markdown("### Selected doc \n\n" + " ".join(text))

    print(selected_doc)

    topic = selected_doc.split("_")[0]

    for doc in doc_ids:
        if doc.startswith(topic) and doc != selected_doc:
            render_doc(doc, gt_documents[doc], sel_clusters)
            break


    render_clusters(gt_chain_by_doc[selected_doc], gt_clusters, "Ground Truth Clusters")
    render_clusters(pred_chain_by_doc[selected_doc], results_clusters, "Predicted Clusters")

def render_doc(doc_id, doc_characters, clusters):

    tok_map = {}

    for cluster_id, cluster in clusters.items():
        for mention in cluster:
            for tok in mention:
                if tok[0] == doc_id:
                    tok_map[int(tok[1])] = cluster_id
    

    markdown = f"### {doc_id}\n\n"

    for i, tok in enumerate(doc_characters):
        if (i in tok_map) and ((i-1) not in tok_map):
            markdown += f"<mark>(**{tok_map[i]}**)"
        
        markdown += " " + tok

        if (i in tok_map) and ((i+1) not in tok_map):
            markdown += "</mark>"

    st.markdown(markdown, unsafe_allow_html=True)


def app_main():

    st.title("Upload files")
    gt_file = st.file_uploader(label="Ground Truth File (conll)")

    gt_clusters = None
    results_clusters = None
    gt_documents = None
    results_documents= None

    if gt_file:
        gt_clusters, gt_documents = parse_conll(gt_file)

        st.text(f"Total clusters: {len(gt_clusters)}")
        show_gt = st.checkbox("Show GT table summary?")
        if show_gt:
            df = generate_cluster_table(gt_clusters)
            st.dataframe(df)

    results_file = st.file_uploader(label="Results (conll)")
    #export_path  = st.text_input(label="Path to json export")

    if results_file:
        results_clusters, results_documents = parse_conll(results_file)
        st.text(f"Total clusters: {len(gt_clusters)}")
        show_results = st.checkbox("Show results table summary?")

        if show_results:
            df = generate_cluster_table(results_clusters)
            st.dataframe(df)
        


    st.title("Analysis Results")
    if results_file and gt_file:
        action_select = st.sidebar.selectbox("View", ["Summary","Deep Dive"])

        if action_select == "Summary":
            analyse_clusters(gt_clusters, results_clusters)
        else:
            deep_dive(gt_clusters, results_clusters, gt_documents, results_documents)
    else:
        st.text("Once you have uploaded both files, the comparison results will appear here")

    

if __name__ == "__main__":
    app_main()