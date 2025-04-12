import requests
from django.conf import settings
from django.shortcuts import render
from django.http import Http404
from requests.exceptions import HTTPError, ConnectionError, Timeout
from datetime import datetime

def video_list(request):
    """Fetch and display a list of recent football video updates from Scorebat."""
    url = f'https://www.scorebat.com/video-api/v3/feed/?token={settings.SCOREBAT_ACCESS_TOKEN}'
    try:
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        response.raise_for_status()
        data = response.json()
        videos = data.get('response', [])
        if not isinstance(videos, list):
            videos = []
        
        processed_videos = []
        for vid in videos:
            if not isinstance(vid, dict):
                print(f"Skipping invalid video entry: {vid}")
                continue
            try:
                vid['date'] = datetime.strptime(vid['date'], '%Y-%m-%dT%H:%M:%S%z')
                vid['video_id'] = vid['videos'][0]['id'] if vid.get('videos') and isinstance(vid['videos'], list) and len(vid['videos']) > 0 else ''
                # Handle competition format
                vid['competition_name'] = vid['competition'] if isinstance(vid['competition'], str) else vid['competition'].get('name', 'Unknown Competition')
                processed_videos.append(vid)
            except (KeyError, ValueError) as e:
                print(f"Error processing video entry: {e} - {vid}")
                continue
        
        print("Processed Videos List Length:", len(processed_videos))
    except HTTPError as e:
        videos = []
        print(f"HTTP Error: {e} - Status Code: {e.response.status_code}")
    except ConnectionError as e:
        videos = []
        print(f"Connection Error: {e}")
    except Timeout as e:
        videos = []
        print(f"Timeout Error: {e}")
    except Exception as e:
        videos = []
        print(f"Unexpected Error: {e}")
    
    return render(request, 'video_list.html', {'videos': processed_videos})

def video_detail(request, video_id):
    """Fetch and display details of a specific football video from Scorebat."""
    url = f'https://www.scorebat.com/video-api/v3/feed/?token={settings.SCOREBAT_ACCESS_TOKEN}'
    try:
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        response.raise_for_status()
        data = response.json()
        videos = data.get('response', [])
        if not isinstance(videos, list):
            raise Http404("Invalid API response: 'response' is not a list")

        # Process and filter videos
        processed_videos = []
        for vid in videos:
            if not isinstance(vid, dict):
                print(f"Skipping invalid video entry: {vid}")
                continue
            try:
                vid['date'] = datetime.strptime(vid['date'], '%Y-%m-%dT%H:%M:%S%z')
                vid['video_id'] = vid['videos'][0]['id'] if vid.get('videos') and isinstance(vid['videos'], list) and len(vid['videos']) > 0 else ''
                processed_videos.append(vid)
            except (KeyError, ValueError) as e:
                print(f"Error processing video entry: {e} - {vid}")
                continue

        # Find the matching video
        video = next((v for v in processed_videos if v.get('video_id') == video_id), None)
        if not video:
            raise Http404(f"Video with ID '{video_id}' not found")
        
        print("Selected Video:", video)

        # Handle competition as string or dict
        competition_name = video['competition'] if isinstance(video['competition'], str) else video['competition'].get('name', 'Unknown Competition')
        
        # Build movie dict
        if 'title' not in video:
            raise Http404("Invalid video data: 'title' missing")
        
        movie = {
            'title': video['title'],
            'release_date': video['date'].strftime('%Y-%m-%d'),
            'overview': f"Highlights from the {competition_name} match between {video['title']}.",
            'genres': [{'name': competition_name}],
            'vote_average': None,
            'runtime': None,
            'thumbnail': video.get('thumbnail', ''),
        }
        trailer = {
            'key': video['videos'][0]['embed'] if video.get('videos') and isinstance(video['videos'], list) and len(video['videos']) > 0 else ''
        }
    except requests.RequestException as e:
        raise Http404(f"Error fetching video: {e}")
    except KeyError as e:
        raise Http404(f"Missing expected key in video data: {e}")
    except Exception as e:
        raise Http404(f"Unexpected error processing video data: {e}")

    return render(request, 'video_detail.html', {
        'movie': movie,
        'trailer': trailer,
        'certification': 'Not Rated'
    })