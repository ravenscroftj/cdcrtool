from cdcrapp import ingest

news_summary = """Dr. James T. Goodrich, a pediatric neurosurgeon known for successfully separating conjoined twins in a complicated and rare procedure, died on Monday at Albert Einstein College of Medicine and Montefiore Medical Center in the Bronx. He was 73.The"""
abstract = """Abstract The Northern Hemisphere dominates our knowledge of Mesozoic and Cenozoic fossilized tree resin (amber) with few findings from the high southern paleolatitudes of Southern Pangea and Southern Gondwana. Here we report new Pangean and Gondwana amber occurrences dating from ~230 to 40 Ma from Australia (Late Triassic and Paleogene of Tasmania; Late Cretaceous Gippsland Basin in Victoria; Paleocene and late middle Eocene of Victoria) and New Zealand (Late Cretaceous Chatham Islands). The Paleogene, richly fossiliferous deposits contain significant and diverse inclusions of arthropods, plants and fungi. These austral discoveries open six new windows to different but crucial intervals of the Mesozoic and early Cenozoic, providing the earliest occurrence(s) of some taxa in the modern fauna and flora giving new insights into the ecology and evolution of polar and subpolar terrestrial ecosystems."""

n = ingest.extract_mentions(news_summary)
s = ingest.extract_mentions(abstract)

model_inputs = ingest.tokenizer.encode_plus(text=news_summary, text_pair=abstract, add_special_tokens=True, return_offsets_mapping=True,max_length=1024,truncation_strategy='only_second')