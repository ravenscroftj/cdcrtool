import requests
import click
import json
import datetime

from cdcrapp import CLIContext
from cdcrapp.model import Task

@click.command()
@click.option("--endpoint", type=str, default="http://localhost:4000/api/newsarticles")
@click.option("--summarizer_endpoint", type=str, default="http://localhost:8000/")
def main(endpoint, summarizer_endpoint):
    """Ingest new tasks from harri core server"""
    
    ctx = CLIContext()
    
    r = requests.get(endpoint)
    response = r.json()
    
    pages = response['totalPages']
    page = 0
    
    for page in range(pages):
        print(f"Page {page+1} of {pages}")
        r = requests.get(endpoint, params={"page":page})
        response = r.json()
        
        for item in response['items']:
            
            print("----------------------")
            
            task = ctx.tasksvc.get_by_filter(Task, news_url=item['url'])
            
            #item must have at least 1 paper with an abstract
            hasAbstract = False
            for paper in item['ScientificPapers']:
                if paper['abstract'] != "":
                    hasAbstract = True
                    break
                
            if not hasAbstract:
                print(f"No papers with abstracts found for article {item['url']}")
                print("skipping...")
                continue
            
            if task is not None:
                print(f"Article {item['title']} - {item['url']} already in database")
            else:
                print(f"Ingest {item['url']}")
                
                # generate summary
                r = requests.post(summarizer_endpoint, json={"text":item['fullText']})
                summary = r.json()['summary']
                
                print(f"Summary for {item['url']}: {summary}")


if __name__ == "__main__":
    main() # pylint: disable=no-value-for-parameter