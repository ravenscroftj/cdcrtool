"""Error analysis module for coreference model outputs"""

import pickle
import json
from typing import List
import itertools
import os
import math
import spacy
import pandas as pd
import streamlit as st 
from collections import defaultdict
from dotenv import load_dotenv
from sqlalchemy import create_engine
from cdcrapp.services import UserService, TaskService
from cdcrapp.model import Task, NewsArticle, SciPaper

FILE_ID_COLUMN = 2
SENT_ID_COLUMN = 3
TOK_ID_COLUMN = 4
TOK_TEXT_COLUMN = 5
CLUSTER_SIGNAL_COLUMN = 7

@st.cache(allow_output_mutation=True)
def load_spacy():
    return spacy.load('en_core_web_sm')

@st.cache(allow_output_mutation=True)
def get_sql_engine():
    return create_engine(os.getenv("SQLALCHEMY_DB_URI"))

load_dotenv()
_engine = get_sql_engine()
_usersvc : UserService = UserService(_engine)
_tasksvc : TaskService = TaskService(_engine)
_nlp : spacy.language.Language = load_spacy()

def msig(mention) -> tuple:
    """Return mention signature for given mention"""
    return mention[0][0], mention[0][1], mention[-1][1]

def muc_score(gt_clusters, pred_clusters):
    """Calculate MUC score - based on number of links between entities
    
    MUC/CONLL co-reference scoring algorithm based on 
    https://www.cs.cmu.edu/~hovy/papers/14ACL-coref-scoring-standard.pdf
    
    """

    R_num = 0
    R_denom = 0

    
    # in the Hovy paper, gt_clusters is 'K'
    for cluster in gt_clusters.values():

        gt_cluster_sigs = set([msig(mention) for mention in cluster])

        R_denom += len(gt_cluster_sigs) -1

        intersecting = 0
        remaining = set(gt_cluster_sigs)
        for pcluster in pred_clusters.values():
            pt_cluster_sigs = set([msig(mention) for mention in pcluster])


            if len(gt_cluster_sigs.intersection(pt_cluster_sigs)) > 0:
                remaining -= gt_cluster_sigs.intersection(pt_cluster_sigs)
                intersecting += 1

        # mop up singletons and spurious mentions
        intersecting += len(remaining)

        R_num += (len(gt_cluster_sigs) - intersecting)

    P_num = 0
    P_denom = 0


    for pcluster in pred_clusters.values():
        pt_cluster_sigs = set([msig(mention) for mention in pcluster])

        P_denom += len(pt_cluster_sigs) - 1

        intersecting = 0
        remaining = set(pt_cluster_sigs)
        for cluster in gt_clusters.values():
            gt_cluster_sigs = set([msig(mention) for mention in cluster])

            if len(gt_cluster_sigs.intersection(pt_cluster_sigs)) > 0:
                remaining -= gt_cluster_sigs.intersection(pt_cluster_sigs)
                intersecting += 1
        # mop up singletons and spurious mentions
        intersecting += len(remaining)
        
        print(f"({len(pt_cluster_sigs)}-{intersecting})")
        print(f"{len(pt_cluster_sigs)} - 1")
        P_num += (len(pt_cluster_sigs) - intersecting)

    
    R = R_num / R_denom if R_denom > 0 else 0
    P = P_num / P_denom if P_denom > 0 else 0

    print("recall:", R)
    print("precision:", P)

    if R + P == 0:
        f1 = 0
    else:
        f1 = 2 * R * P / (R+P)

    return R,P,f1
    

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
            #print("------------------------------------------------")
            #print(gt_neighbours,"\n---\n", pred_neighbours)

    st.markdown(f"## Coreference Resolution\n\n### Absolute Performance")

    st.text(f"Correct co-reference chains: {correct}/{len(correct_mentions )} ({round(correct/len(correct_mentions )*100, 2)}%)")
    st.text(f"Total intra-document chains: {total_intra} Correct intra-document chains: {correct_intra} ({round(correct_intra/total_intra,2)}%)")
    st.text(f"Total cross-document chains: {total_cross} Correct cross-document chains: {correct_cross} ({round(correct_cross/total_cross,2)}%)")

    recall, precision, f1 = muc_score(gt_clusters, pred_clusters)

    st.markdown(f"### MUC Performance \n Recall: {recall}\n\n Precision: {precision}\n\n F1:{f1}")


def render_clusters(cluster_ids, clusters, title):
    markdown = f"## {title}\n\n"
    for cluster_id in cluster_ids:
        mentions = []
        markdown += f" - {cluster_id}\n"
        for mention in clusters[cluster_id]:
            doc = mention[0][0]
            markdown += f"   - {' '.join([word[2] for word in mention])} ({doc})\n" 
    
    st.sidebar.markdown(markdown)
    


def map_tasks_to_mentions(tasks: List[Task], newsdoc: spacy.tokens.doc.Doc, scidoc: spacy.tokens.doc.Doc):

    taskmap = {}


    for task in tasks:
        _, start, end = task.news_ent.split(";")
        start = int(start)
        end = int(end)

        news_words = []
        sci_words = []
        for doc, dtype in ((newsdoc,'news'), (scidoc,'science')):
            for word in doc:

                if word.idx >= start:
                    taskmap[(dtype, word.i)] = task.hash
                
                if len(word) + word.idx >= end:
                    break

    return taskmap 



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

    pair_doc = None
    topic = selected_doc.split("_")[0]
    for doc in doc_ids:
        if doc.startswith(topic) and doc != selected_doc:
            pair_doc = doc
            break

    if "news" in selected_doc:
        news_id = selected_doc.split("_")[2]
        sci_id = pair_doc.split("_")[2]
    else:
        sci_id = selected_doc.split("_")[2]
        news_id = pair_doc.split("_")[2]
    
    with _tasksvc.session() as session:
        tasks = session.query(Task).filter(Task.news_article_id==news_id, Task.sci_paper_id==sci_id, Task.is_bad == False).all()
        news_db_obj = session.query(NewsArticle).get(news_id)
        sci_db_obj = session.query(SciPaper).get(sci_id)

        newsdoc = _nlp(news_db_obj.summary)
        scidoc = _nlp(sci_db_obj.abstract)
        
        #taskmap = map_tasks_to_mentions(tasks, newsdoc, scidoc)
        

    text = gt_documents[selected_doc]

    selected_clusterset = st.sidebar.selectbox("Cluster set", ["Both", "Ground Truth","Predicted"])

    gt_cluster_ids = list(gt_chain_by_doc[selected_doc]) + list(gt_chain_by_doc[pair_doc]) 
    gt_doc_clusters = {cluster_id: gt_clusters[cluster_id] for cluster_id in gt_cluster_ids}

    pred_cluster_ids = list(pred_chain_by_doc[selected_doc]) + list(pred_chain_by_doc[pair_doc])
    pred_doc_clusters = {cluster_id: results_clusters[cluster_id] for cluster_id in pred_cluster_ids}


    if selected_clusterset == "Ground Truth":
        render_clusterlist = [gt_doc_clusters]
    elif selected_clusterset == "Predicted":
        render_clusterlist = [{}, pred_doc_clusters]
    else:
        render_clusterlist = [gt_doc_clusters, pred_doc_clusters]

    render_doc(selected_doc, text, render_clusterlist)

    #st.markdown("### Selected doc \n\n" + " ".join(text))

    if pair_doc != None:
        render_doc(pair_doc, gt_documents[doc], render_clusterlist)

    render_clusters(gt_chain_by_doc[selected_doc], gt_clusters, "Ground Truth Clusters")
    render_clusters(pred_chain_by_doc[selected_doc], results_clusters,"Predicted Clusters")

    gt = {cluster_id: gt_clusters[cluster_id] for cluster_id in gt_chain_by_doc[selected_doc]}
    pred = {cluster_id: results_clusters[cluster_id] for cluster_id in pred_chain_by_doc[selected_doc]}

    recall, precision, f1 = muc_score(gt, pred)

    st.markdown(f"MUC Recall: {recall}, MUC Precision: {precision}, MUC F1: {f1}")

    st.header("Review")

    ent1 = st.selectbox("Cluster",["---"] + gt_cluster_ids)
    #ent2 = st.selectbox("Cluster 2",["---"] + gt_cluster_ids)

    if ent1 != "---":
        news_words = [word for word in newsdoc if not word.text.strip() == ""]
        sci_words = [word for word in scidoc if not word.text.strip() == ""]


        doc_ents = []

        for mention in gt_clusters[ent1]:
            if "news" in mention[0][0]:
                doc = newsdoc
                words = news_words
            else:
                doc = scidoc
                words = sci_words
            start_idx = int(mention[0][1])
            end_idx = int(mention[-1][1])
            ent_words = words[start_idx:end_idx+1]
            text = " ".join([w.text for w in ent_words])

            start_offset = ent_words[0].idx
            end_offset = ent_words[-1].idx + len(ent_words[-1])
            text  = doc.text[start_offset:end_offset]
            
            ent = f"{text};{start_offset};{end_offset}"

            doc_ents.append((mention[0][0],ent))

        task_map = {(task.news_ent,task.sci_ent):task for task in tasks}

        rows = []

        #print(task_map)


        for dent1, dent2 in itertools.combinations(doc_ents, 2):

            if ("news" in dent1[0] and "news" in dent2[0]) or ("science" in dent1[0] and "science" in dent2[0]):
                continue
            elif "news" in dent1[0]:
                news_ent = dent1
                sci_ent = dent2
            else:
                news_ent = dent2
                sci_ent = dent1
            
            print(news_ent[1], sci_ent[1])
            task = task_map.get((news_ent[1], sci_ent[1]))


            if task:
                rows.append((task.id, task.hash, news_ent[1], sci_ent[1]))

        df = pd.DataFrame(rows, columns=['Task ID', 'Task Hash', 'News Entity', 'Science Entity'])
            

        st.table(df)





def blend_colours(col1, col2):
    """Take the average of 2 colours"""

    newcol = []

    if col1.startswith("#"):
        col1 = col1[1:]

    if col2.startswith("#"):
        col2 = col2[1:]
    
    for s,e in [(0,2),(2,4),(4,6)]:
        tone1 = int(col1[s:e],16)
        tone2 = int(col2[s:e],16)

        middle = (max(tone1,tone2) - min(tone1,tone2)) // 2

        halfway = min(tone1,tone2) + middle

        newcol.append(hex(halfway)[2:].rjust(2,'0'))

    return "#"+"".join(newcol)



def render_doc(doc_id, doc_characters, cluster_sets):

    tok_map = {}

    colours = ['#fcf8e3','#9fc9ff']

    for clusters, colour in zip(cluster_sets, colours):
        for cluster_id, cluster in clusters.items():
            for mention in cluster:
                for tok in mention:
                    if tok[0] == doc_id:
                        if int(tok[1]) in tok_map:
                            prev_cluster,prev_color = tok_map[int(tok[1])] 
                            tok_map[int(tok[1])] = (cluster_id + "|" + prev_cluster, blend_colours(colour, prev_color))
                        else:
                            tok_map[int(tok[1])] = (cluster_id, colour)
    

    markdown = f"### {doc_id}\n\n"

    for i, tok in enumerate(doc_characters):
        if (i in tok_map) and ((i-1) not in tok_map):
            markdown += f"<mark style='background-color: {tok_map[i][1]}'>(**{tok_map[i][0]}**)"
        
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