import requests
import bs4 as bs 

# Script to download videos once the URLs are obtained.
# The problem is that getting the URLs is not straightforward, the web crawler is in the notebook.

# The URL has the following form:
'...media/YEAR/MONTH/DAY/PLAYER_ID/'
# Video URL
video_url = "https://videos.nba.com/nba/pbp/media/2024/11/12/0022400005/20/7ac52325-8749-0f24-fee9-c90ad6c85274_1280x720.mp4"

# Download the video file
response = requests.get(video_url, stream=True)

# Save the file
with open("nba_video.mp4", "wb") as file:
    for chunk in response.iter_content(chunk_size=8192):
        file.write(chunk)

print("Video downloaded successfully!")