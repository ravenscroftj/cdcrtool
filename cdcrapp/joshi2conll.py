import json
import click
import typing
from collections import defaultdict

test_str = ["[CLS]", "these", "findings", "illustrate", "the", "potential", "for", "next", "-", "generation", "se", "##quencing", "to", "provide", "unprecedented", "insights", "into", "mutation", "##al", "processes", ",", "cellular", "repair", "pathways", "and", "gene", "networks", "associated", "with", "cancer", ".", "[SEP]"]

def tidy_up_tokens(bert_tokens, special_characters=['[CLS]','[SEP]']):
    """Return normal english words from bert subword tokens"""
    words = []
    accum = ""
    for tok in bert_tokens:

        if tok.startswith("##"):
            accum += tok[2:]
            continue

        elif len(accum) > 0:
            words.append(accum)

        accum = tok

    if len(accum) > 0:
        words.append(accum)
    
    return words

def test_tidy_up():
    print(tidy_up_tokens(test_str))

@click.command()
@click.argument("input_file", type=click.File(mode="r"))
@click.argument("output_file", type=click.File(mode="w"))
def main(input_file: typing.TextIO, output_file: typing.TextIO):
    """Convert joshi to conll"""

    output_file.write("#begin document test_entities\n")

    topic = 0
    next_cluster = 0
    for line in input_file:
        doc = json.loads(line)
        tok_offset = 0
        word_offset = 0
        sent_offset = 0

        word_mapping = defaultdict(lambda:[])
        sent_mentions = set()

        doclen = len(doc["subtoken_map"])


        for clst_id, clst in enumerate(doc['predicted_clusters'], start=next_cluster):

            for start,end in clst:

                if (start >= doclen) or (end >= doclen):
                    continue


                print(start,end)
                sent_mentions.update([doc['sentence_map'][start], doc['sentence_map'][end]])
                if start == end:
                    word_mapping[start].append(f"({clst_id})")
                else:
                    word_mapping[start].append(f"({clst_id}")
                    word_mapping[end].append(f"{clst_id})")

        next_cluster += len(doc['predicted_clusters'])

        for sent in doc['sentences']:

            doc_id = doc['doc_ids'][0] if tok_offset < doc['doc_boundaries'][1] else doc['doc_ids'][1]

            words = tidy_up_tokens(sent)

            sent_flag = "True" if sent_offset in sent_mentions else "False"

            for word in words:

                if word in ['[CLS]','[SEP]']:
                    tok_offset += 1
                    continue

                cluster_str = "|".join(word_mapping[tok_offset]) if tok_offset in word_mapping else "-"
                
                row = [str(topic), f"{topic}_0", f"{topic}_{doc_id}", str(sent_offset), str(word_offset), word, sent_flag, cluster_str]
                output_file.write("\t".join(row) + "\n")               

                tok_offset += 1
                word_offset += 1

            sent_offset += 1

    output_file.write("#end document")

        

if __name__ == "__main__":
    main()