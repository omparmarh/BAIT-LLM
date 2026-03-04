import requests
import json
from typing import Dict

def web_search(query: str):
    """Search the web for information using DuckDuckGo and Wikipedia."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # 1. Try DuckDuckGo
        search_url = f"https://duckduckgo.com/?q={query.replace(' ', '+')}&format=json"
        try:
            response = requests.get(search_url, headers=headers, timeout=5)
            data = response.json()
            if data.get('AbstractText'):
                return f"Summary: {data['AbstractText']}\nSource: DuckDuckGo"
        except:
            pass
            
        # 2. Try Wikipedia
        wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={query}&format=json"
        try:
            response = requests.get(wiki_url, headers=headers, timeout=5)
            wiki_data = response.json()
            if wiki_data.get('query', {}).get('search'):
                top_result = wiki_data['query']['search'][0]
                snippet = top_result['snippet'].replace('<span class="searchmatch">', '').replace('</span>', '')
                return f"Wikipedia [Title: {top_result['title']}]: {snippet}"
        except:
            pass
            
        return f"I couldn't find specific web results for '{query}'. Try rephrasing."
    except Exception as e:
        return f"Error during web search: {str(e)}"
