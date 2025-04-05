import requests
import pandas as pd
import argparse
from lxml import etree

PUBMED_API_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

def fetch_pubmed_ids(query):
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": 50,
        "email": "sathishbolavena@gmail.com"  # Your email
    }
    response = requests.get(PUBMED_API_URL, params=params)
    data = response.json()
    return data.get("esearchresult", {}).get("idlist", [])

def parse_paper(xml_content):
    root = etree.fromstring(xml_content)
    papers = []
    
    for article in root.xpath('//PubmedArticle'):
        pmid = article.xpath('.//PMID/text()')[0]
        title = " ".join(article.xpath('.//ArticleTitle/text()'))
        authors = []
        
        for author in article.xpath('.//Author'):
            name = " ".join(filter(None, [
                author.xpath('./LastName/text()'),
                author.xpath('./ForeName/text()')
            ]))
            affil = author.xpath('./Affiliation/text()')
            if name and affil:
                authors.append({
                    "name": name[0] if isinstance(name, list) else name,
                    "affiliation": affil[0] if affil else ""
                })
        
        papers.append({
            "pmid": pmid,
            "title": title,
            "authors": authors
        })
    return papers

def get_papers(query, filename=None):
    pubmed_ids = fetch_pubmed_ids(query)
    if not pubmed_ids:
        print("No papers found")
        return

    print(f"Found PubMed IDs: {pubmed_ids}")
    
    params = {
        "db": "pubmed",
        "id": ",".join(pubmed_ids),
        "retmode": "xml"
    }
    response = requests.get(EFETCH_URL, params=params)
    papers = parse_paper(response.content)
    
    # Filter for industry affiliations
    industry_keywords = ["pfizer", "novartis", "pharma", "biotech", "inc"]
    results = []
    
    for paper in papers:
        for author in paper["authors"]:
            affil = author["affiliation"].lower()
            if any(kw in affil for kw in industry_keywords):
                results.append([
                    paper["pmid"],
                    paper["title"],
                    ", ".join(a["name"] for a in paper["authors"]),
                    author["affiliation"]
                ])
                break
    
    if results:
        df = pd.DataFrame(results, columns=["PubMedID", "Title", "Authors", "Industry Affiliation"])
        if filename:
            df.to_csv(filename, index=False)
            print(f"Results saved to {filename}")
        else:
            print(df.to_string(index=False))
    else:
        print("No papers with industry affiliations found")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="PubMed search query")
    parser.add_argument("-f", "--file", help="Output CSV file")
    args = parser.parse_args()
    get_papers(args.query, args.file)