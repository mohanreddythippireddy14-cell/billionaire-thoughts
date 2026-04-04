import sys
import os

# Reuse uploader from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from uploader import upload_video

from wisdom_quotes.quote_engine import get_next_quote
from wisdom_quotes.video_creator import create_video


def run():
    print("=== Wisdom Quotes Pipeline ===")

    quote = get_next_quote()
    print(f"Quote: {quote}")

    video_path = create_video(quote)

    # Use first ~60 chars of quote as title
    title = quote[:60] + "..." if len(quote) > 60 else quote
    description = (
        f"{quote}\n\n"
        "#wisdom #quotes #motivation #philosophy #shorts"
    )
    tags = ["wisdom", "quotes", "motivation", "philosophy", "shorts", "mindset"]

    upload_video(
        video_path=video_path,
        title=title,
        description=description,
        tags=tags,
        category_id="27",  # Education
    )

    print("=== Done ===")


if __name__ == "__main__":
    run()
