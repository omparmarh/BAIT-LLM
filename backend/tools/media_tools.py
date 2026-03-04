import subprocess
import urllib.parse

def play_youtube_music(query: str = "trending music India"):
    """
    Search and play music on YouTube.
    If query is empty, it plays trending music in India.
    """
    try:
        # Construct the YouTube search URL
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.youtube.com/results?search_query={encoded_query}"
        
        # If the user wants "trending", we can actually point to the trending music page
        if "trending" in query.lower() and "india" in query.lower():
            url = "https://www.youtube.com/feed/trending?bp=4gINGgt5dG1hX2NoYXJ0cw%3D%3D" # Direct trending music link

        # Use macOS 'open' command
        subprocess.run(["open", url], check=True)
        return f"Opening YouTube to play: {query}"
    except Exception as e:
        return f"Error playing music on YouTube: {str(e)}"

if __name__ == "__main__":
    # Test
    print(play_youtube_music("Arijit Singh hits"))
