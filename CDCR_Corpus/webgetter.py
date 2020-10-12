
#%%
import json
import os
import time
import argparse
import math
import re
from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag
import requests
from typing import List, Union
from newspaper import Article


UA_STRING = "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:77.0) Gecko/20100101 Firefox/77.0"


site_patterns = {
    "bbc.co.uk": [".story-body__inner p",'div[data-component="text-block"] p',".story-inner p",],
    "guardian": ".content__article-body p",
    "eurekalert": ".entry p",
    "nytimes": ".StoryBodyCompanionColumn p"
}

def get_child_text(selection):
    for child in selection:
        yield child.text
        #for content in child.contents:
        #    if type(content) == NavigableString:
        #        yield content
        #    elif type(content) == Tag:
        #        for item in get_child_text([content]):
        #            yield item

def get_body_text(url: str, css_selector: Union[str,List[str]], user_agent: str=UA_STRING) -> str:
    r = requests.get(url, headers={
        "User-Agent": UA_STRING
    })
    bs = BeautifulSoup(r.text, features='lxml')

    if type(css_selector) == str:
        css_selector = [css_selector]

    best_text = ""
    best_length = 0
    for selector in css_selector:

        texts = get_child_text(bs.select(selector))
        body_text = " ".join([t.strip() for t in texts])
        #body_text = re.sub(r"[^\S]+", " ", body_text)

        if len(body_text) > best_length:
            best_text = body_text
            best_length = len(body_text)

    return best_text

def get_selector(url) -> str:

    for url_snippet, selector in site_patterns.items():

        if url_snippet in url:
            return selector
    
    return None

def fetch_news_articles(urls: List[str], outfile: str, wait: int, user_agent:str=UA_STRING, legacy: List[int]=[]):

    existing_docs = {}
    
    if os.path.exists(outfile):
        with open(outfile) as f:
            try:
                existing_docs = json.load(f)
            except:
                print("Could not load existing docs - re-initializing")
                
    
    start_time = time.time()

    for i, url in enumerate(urls):
        avg_time = round((time.time() - start_time) / (i+1),2)
        remaining = math.floor(avg_time * (len(urls) - i - 1) / 60)

        print(f"[{i+1}/{len(urls)}] Fetch content for {url}...")
        print(f"[{avg_time}s per article - est. {remaining} minutes remaining]")

        if existing_docs.get(url,"") != "":
            print(f"Skipping content for existing doc {url}")
            continue

        selector = get_selector(url)

        if not selector or i in legacy:
            print(f"Using newspaper for {url}")
            article = Article(url)
            try:
                article.download()
                article.parse()
            except:
                print(f"Failed to get {url}")
            existing_docs[url] = article.text
        else:
            existing_docs[url] = get_body_text(url, selector, user_agent=user_agent)

        with open(outfile,'w') as f:
            json.dump(existing_docs, f, indent=2)
        
        time.sleep(wait)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("input_file", help="Name of input json file containing urls to download")
    ap.add_argument("output_file", help="name of output file for storage of HTML")
    ap.add_argument("--wait", type=int, help="Number of seconds to wait between requests (default 5)", default=5)
    ap.add_argument("--user-agent", type=str, help="Set user agent string used for retrieval of articles", default=UA_STRING)
    args = ap.parse_args()

    with open(args.input_file,'r') as f:
        news_articles = json.load(f)

        # just get list of urls from id:{url:'...'} structure
        urls = [article['url'] for _, article in news_articles.items()]
        legacy = [i for i, (_, article) in enumerate(news_articles.items()) 
            if article.get('legacy', False)]

        print(legacy)

        fetch_news_articles(urls, args.output_file, args.wait, args.user_agent, legacy=legacy)
# %%
