import streamlit as st
import requests
import pandas as pd
import datetime
import webp
from pathlib import Path

URL = "https://www.verticalradio.ch/api/search?locale=fr&site=1&status[]=2&count=20&types[]=music_tracks&orderByProperty=dateFrom&orderByDirection=DESC&page={}&children=false&return_null_properties=false&embed_medias=true&embed_medias_new_format=true&date_search_on_period=false"
IMAGE_URL = "https://www.verticalradio.ch/media/image/{}/medium_1_1/{}.{}.webp?{}="
DATA_FILE = Path("vertical_radio_tracks.csv")

st.title("Vertical Radio Music Tracks")

def get_image_url(data):
    try:
        im_data = data["aio:images"][0]
        return IMAGE_URL.format(im_data["folder"], im_data["fileName"], im_data["extension"], im_data["hash"])
    except KeyError as e:
        return None

def get_image(data):
    im_url = get_image_url(data)
    if not im_url:
        return None
    return webp.WebPData.from_buffer(requests.get(im_url).content).decode(color_mode=webp.WebPColorMode.BGR)

def get_latest_tracks(most_recent=None):
    latest_iteration = st.empty()
    tracks = []
    i = 0
    while True:
        try:
            response = requests.get(URL.format(i+1)).json()
            _tracks = [[track["artist"], track["title"], datetime.datetime.fromisoformat(track["readDate"]), get_image_url(track)] for track in response['hydra:member']]

            if most_recent:
                _tracks = [track for track in _tracks if track[2] > most_recent]

            tracks.extend(_tracks)
            if not _tracks:
                break
        except Exception as e:
            break
        # Safety break to avoid infinite loops
        if i > 1000:
            break
        i += 1
        
    del latest_iteration

    df = pd.DataFrame(tracks, columns=["Artist", "Title", "Date", "Image"])

    return df

def load_data():
    if DATA_FILE.exists():
        existing_df = pd.read_csv(DATA_FILE, parse_dates=["Date"])
        most_recent_date = existing_df["Date"].max()
        new_tracks_df = get_latest_tracks(most_recent=most_recent_date)
        if not new_tracks_df.empty:
            updated_df = pd.concat([existing_df, new_tracks_df], ignore_index=True)
            updated_df.to_csv(DATA_FILE, index=False)
        else:
            updated_df = existing_df
    else:
        updated_df = get_latest_tracks()
        updated_df.to_csv(DATA_FILE, index=False)

    return updated_df

df = load_data()


search = st.text_input("Search for an artist:", key="search_input")
search_btn = st.button("Search")

if search_btn:
    if search:
        filtered_df = df[df['Artist'].str.contains(search, case=False)].groupby(['Title']).agg({'Date': 'max', 'Artist': 'count', 'Image': 'first'}).reset_index()
        st.dataframe(
            filtered_df.sort_values(by='Artist', ascending=False),
            hide_index=True,
            row_height=100,
            height="stretch",
            column_order=["Image", "Title", "Date", "Artist"],
            column_config={
                "Date": st.column_config.DatetimeColumn("Last on air", format="distance"),
                "Artist": st.column_config.NumberColumn("Count"),
                "Image": st.column_config.ImageColumn("Cover", width=100),
            }
        )

    else:
        st.warning("Please enter a search term.")

