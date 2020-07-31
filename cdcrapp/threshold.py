"""Make threshold predictions"""
import json
import os
import sys
import itertools
import torch
from tqdm.auto import tqdm
import numpy as np

from collections import defaultdict
from export import get_next_cluster_id

from ingest import tokenizer,model,get_tokens_by_offset,cosine

def predict_threshold(data_file, threshold=0.6):
    """Given a data file, make a series of predictions"""

    with open(data_file,"r") as f:
        docs = json.load(f)

    fname,ext = os.path.splitext(data_file)

    ents_file = fname + "_entities" + ext

    with open(ents_file,"r") as f:
        ents = json.load(f)


    topic_map = defaultdict(lambda:[])

    for doc in docs.keys():
        topic = doc.split("_")[0]
        topic_map[topic].append(doc)

    msent = lambda mention: [  word for word in docs[mention['doc_id']] if word[0] == mention['sentence_id']]

    mention_map = {}

    for topic, topic_pair in tqdm(topic_map.items()):

        groupchains = []

        mentions = [ (ent_id, ent) for ent_id, ent in enumerate(ents) if ent['doc_id'] in topic_pair]

        for (m1_id, m1), (m2_id, m2) in itertools.combinations(mentions, 2):
            sent1 = msent(m1)
            sent2 = msent(m2)

            sent1_len = sum([len(tok[2]) for tok in sent1])
            sent1_text = " ".join([tok[2] for tok in sent1])

            sent2_text = " ".join([tok[2] for tok in sent2])

            model_inputs = tokenizer.encode_plus(text=sent1_text, text_pair=sent2_text, 
                add_special_tokens=True, 
                return_offsets_mapping=True,
                max_length=512,
                truncation_strategy='only_second')

            # run single pass of BERT with both documents to get attention matrices
            with torch.no_grad():
                    hidden_state, out = model(
                        input_ids=torch.tensor([model_inputs['input_ids']]).cuda(), 
                        token_type_ids = torch.tensor([model_inputs['token_type_ids']]).cuda(),
                        attention_mask = torch.tensor([model_inputs['attention_mask']]).cuda()
                    )

            state = hidden_state.squeeze()

            vectors = []

            for i, (mention, sent) in enumerate([(m1, sent1),(m2,sent2)]):
                sent_word_offset = sent[0][1]
                token_word_offsets = [w - sent_word_offset for w in mention['tokens_ids']]
                start_char_offset = sum([len(w[2]) for w in sent[:token_word_offsets[0]]]) + token_word_offsets[0]
                end_char_offset = sum([len(w[2]) for w in sent[:token_word_offsets[-1]+1]]) + token_word_offsets[-1]

                second = i == 1
                
                tokens = list(get_tokens_by_offset(start_char_offset,end_char_offset, model_inputs, second_doc=second))
                vec = np.mean(np.array([state[i].cpu().numpy() for (i,_) in tokens]), axis=0)

                vectors.append(vec)

            sim = 1-cosine(*vectors)

            #print(m1['tokens'],m2['tokens'],sim)

            is_coref = sim > threshold

            resolved_m1 = False
            resolved_m2 = False
            related_chains = set()

            for i, chain in enumerate(groupchains):

                if m1_id in chain:
                    resolved_m1 = True
                    related_chains.add(i)
                # controversially not an elif because someone else might have linked these two things
                if m2_id in chain:
                    resolved_m2 = True
                    related_chains.add(i)
                    
                if resolved_m1 and resolved_m2:
                    break

            if is_coref:
                    
                merge_set = set([m1_id, m2_id])
                # it's important we sort descending so that we don't pop stuff we need and get off by 1 errors
                for chain_id in sorted(related_chains, reverse=True):
                    merge_set = merge_set.union(groupchains.pop(chain_id))

                groupchains.append(merge_set)


            if not(resolved_m1 or is_coref):
                groupchains.append(set([m1_id]))

            if not (resolved_m2 or is_coref):
                groupchains.append(set([m2_id]))

        
        for chain in groupchains:
            cluster_id = get_next_cluster_id()
            for member in chain:
                mention_map[member] = cluster_id

    new_ents = [e for e in ents]

    for ent_id, ent in enumerate(new_ents):
        ent['cluster_id'] = mention_map[ent_id]

    with open("pred.json","w") as f:
        json.dump(new_ents, f)


        
if __name__ == "__main__":

    predict_threshold(sys.argv[1])