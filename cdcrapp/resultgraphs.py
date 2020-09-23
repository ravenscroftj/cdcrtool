# %%
from dotenv import load_dotenv
from collections import Counter
from matplotlib import pyplot as plt

from sqlalchemy import create_engine

import os
import json
import numpy as np
import pandas as pd
import seaborn as sns
from cdcrapp.services import UserService, TaskService
from cdcrapp.model import User, Task, UserTask, NewsArticle, SciPaper


load_dotenv()

sns.set_style()

pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', 200)

pd.options.display.max_colwidth = 200

_engine = create_engine(os.getenv("SQLALCHEMY_DB_URI"))
_usersvc : UserService = UserService(_engine)
_tasksvc : TaskService = TaskService(_engine)
# %%
def get_task_sims():

    annotated = _tasksvc.get_annotated_tasks()

    sims = []
    for task in annotated:

        if task.similarity == None:
            continue
        
        if len(task.usertasks) == 1:
            sims.append((task.similarity, task.usertasks[0].answer))
        else:
            answers = Counter([ut.answer for ut in task.usertasks])

            sims.append((task.similarity, answers.most_common(1)[0][0]))

    return sims

sims = get_task_sims()
# %%

df = pd.DataFrame.from_records(sims, columns=['Similarity','Co-referent'])

#df = df[(df.Similarity > 0.4) & (df.Similarity < 0.8)]

#sns.distplot(df['Similarity'], hue="answer", color="red")
#sns.distplot(df[df.Answer=='No']['Similarity'], color="skyblue")

g = sns.FacetGrid(df, hue="Co-referent", height=5, aspect=1.2, legend_out=True)

from scipy.stats import norm
g.map(sns.distplot, "Similarity", kde=False)
plt.legend()
plt.ylabel("Frequency")
plt.show()
#st.pyplot()
#st.dataframe(df)
# %%
#df.plot(kind='hist', )
plt.figure(figsize=(10,10))
df.boxplot(column='Similarity',by='Answer', figsize=(10,10))
# %%
plt.rcParams["figure.figsize"] = (5,7)
sns.boxplot(x='Answer',y='Similarity', data=df)
# %%
~