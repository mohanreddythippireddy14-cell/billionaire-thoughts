import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from youtube_uploader import upload_to_youtube

from wisdom_quotes.quote_engine import get_next_quote
from wisdom_quotes.video_creator import create_video

def run():
    print("=== Wisdom Quotes Pipeline ===")

    quote = get_next_quote()
    print(f"Quote: {quote}")

    video_path = create_video(quote)

    title = quote[:60] + "..." if len(quote) > 60 else quote

    content_data = {
        "title": title,
        "hook": quote,
        "content": quote,
    }

    upload_to_youtube(video_path=video_path, content_data=content_data)

    print("=== Done ===")

if __name__ == "__main__":
    run()
