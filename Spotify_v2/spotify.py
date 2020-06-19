import json
import requests
import os

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import youtube_dl

from client_secret import spotify_token, spotify_user_id

spotify_api = "https://api.spotify.com/v1/users/{}/playlists"
spotify_api_search = "https://api.spotify.com/v1/search?query=track%3A{}+artist%3A{}&type=track&offset=0&limit=20"


class CreatePlaylist:

    def __init__(self):
        #self.user_id = spotify_user_id
        #self.spotify.token = spotify_token
        self.youtube_client = self.get_youtube_client()
        self.all_song_info = {}  # creating a dictionary for all the songs in the liked playlist on youtube

    # step 1 - log into YouTube
    def get_youtube_client(self):
        # Log into Youtube client
        # This must be removed in production. Only for testing purposes.
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        api_service_name = "youtube"
        api_version = "v3"
        client_secret_file = "client_secret.json"

        # create a scope which will give my app access to my youtube account on a readonly permission
        scopes = ["https://www.googleapis.com/auth/youtube.readonly"]

        # Acquiring user credentials by running the OAuth 2.0 authorisation flow and InstalledAppFlow
        # is the flow used when working on desktop apps:
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            client_secret_file, scopes)
        credentials = flow.run_console()

        # If the credentials are entered correctly in the console, to the request access via the API (youtube, v3)
        youtube_client = googleapiclient.discovery.build(api_service_name, api_version, credentials=credentials)

        return youtube_client

    # step 2 - go into libraries / playlists in Youtube to get songs (Getting info from YouTube API)
    def get_liked_videos(self):
        request = self.youtube_client.videos().list(
            part="snippet, contentDetails, statistics",
            myRating="like"
        )
        response = request.execute()
        # When making the request to the account, to go to the like videos and collect them in response

        # Loop through each item in response and asign the following information. Working within a dictionary.
        for item in response["items"]:
            video_title = item["snippet"]["title"]  # gets the title of a song
            youtube_url = "https://www.youtube.com/watch?v={}".format(
                item["id"])  # gets the unique id of a song and adds it to the url

            video = youtube_dl.YoutubeDL({}).extract_info(youtube_url, download=False)
            # Using youtubedl to extract the necessary information to send to spotify to make the playlist
            song_name = video["track"]
            artist = video["artist"]

            self.all_song_info[video_title] = {
                "youtube_url": youtube_url,
                "song_name": song_name,
                "artist": artist,

                "spotify_search": self.search_song(song_name, artist)
            }

    # step 3 - create playlist (Spotify API)
    def create_playlist(self):
        request_body = json.dumps({
            "name": "YouTube Liked Videos",
            "description": "These are my liked videos from YouTube",
            "public": False
        })  # This is creating the Spotify playlist with the Json criteria.

        http_request = spotify_api.format(
            self.user_id)  # essentially http_request = https://api.spotify.com/v1/users/{}/playlists - with my unique id where the {} are
        response = requests.post(
            http_request,
            data=request_body,
            headers={
                "Content-Type": "application/json",
                "Authorisation": "Bearer {}".format(spotify_token)
            }
        )

        response_json = response.json()

        # This playlist ID helps us add specific songs to the playlist
        return response_json["id"]

    # step 4 - search for song in spotify
    def search_song(self, song_name, artist):
        song_request = spotify_api_search.format(song_name, artist)
        response = requests.get(
            song_request,
            headers={
                "Content-Type": "application/json",
                "Authorisation": "Bearer {}".format(self.spotify_token)
            }
        )

        response_json = response.json()
        songs = response_json["tracks"]["items"]

        # Only using the first song

        uri = songs[0]["uri"]  # first song as uri and saving it to uri variable. So the playlist
        return uri  # knows what specific songs to add

    # step 5 - Add song to playlist
    def add_song_to_playlist(self):
        # populate the songs dictionary
        self.get_liked_videos()

        # collect all the song uri and info in a list
        uris = []
        for song, info in self.all_song_info.items():
            uris.append(info["spotify_search"])

        # create a new playlist
        playlist_id = self.create_playlist()

        # add all songs into new playlist
        request_data = json.dumps(uris)
        query = "https://api.spotify.com/v1/playlists/{}/tracks".format(playlist_id)
        response = requests.post(
            query,
            data=request_data,
            headers={
                "Content-Type": "application/json",
                "Authorisation": "Bearer {}".format(self.spotify_token)
            })
        response_json = response.json()
        return response_json


if __name__ == '__main__':
    cp = CreatePlaylist()
    cp.add_song_to_playlist()
