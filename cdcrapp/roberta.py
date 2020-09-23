# %%
import pandas as pd
import seaborn as sns

from matplotlib import pyplot as plt

# %%

df = pd.read_csv("../scibert_sim.csv")
ro_df = pd.read_csv("../roberta_sim.csv")
# %%
df.columns
# %%
df.roberta_sim
# %%
line = sns.distplot(df.scibert_sim, kde=False, label="SCiBERT")
line2 = sns.distplot(df.similarity, kde=False, label="BERT")


plt.legend()

# %%
df[df.id==93866	]
# %%
ro_df[ro_df.id==93866]
# %%
