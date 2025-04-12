import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime


# DB config
DB_HOST = "spotify-etl-db.c5ogo2oke3oq.ap-southeast-1.rds.amazonaws.com"
DB_NAME = "postgres"
DB_USER = "darren"
DB_PASSWORD = "robiglesc"
DB_PORT = "5432"

# Connect to PostgreSQL
conn = psycopg2.connect(
    host=DB_HOST,
    database=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    port=DB_PORT
)

# 1. Top 5 Artists
top_artists = pd.read_sql("""
    SELECT artist, COUNT(*) AS play_count
    FROM spotify_history
    GROUP BY artist
    ORDER BY play_count DESC
    LIMIT 5;
""", conn)

# 2. Total Minutes Today
minutes_today = pd.read_sql("""
    SELECT
    SUM(duration_ms) AS total_duration_ms
    FROM spotify_history
    WHERE (played_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Singapore')::date = (NOW() AT TIME ZONE 'Asia/Singapore')::date;
""", conn)
duration_ms = int(minutes_today['total_duration_ms'][0] or 0)
hours = duration_ms // (1000 * 60 * 60)
minutes = (duration_ms % (1000 * 60 * 60)) // (1000 * 60)
total_time_today = f"{hours} hr {minutes} min"

# 3. Weekly Listening Trend (Ensure 0 value for no data days and include current day)
weekly = pd.read_sql("""
    WITH date_range AS (
        SELECT generate_series(
            (NOW() AT TIME ZONE 'Asia/Singapore')::date - INTERVAL '6 days', 
            (NOW() AT TIME ZONE 'Asia/Singapore')::date,  -- Ensure current date (Singapore time) is included
            '1 day'::interval
        )::date AS date
    )
    SELECT 
        dr.date,
        COALESCE(SUM(sh.duration_ms), 0) AS total_duration_ms
    FROM date_range dr
    LEFT JOIN spotify_history sh
        ON (sh.played_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Singapore')::date = dr.date
    GROUP BY dr.date
    ORDER BY dr.date;
""", conn)

# Convert milliseconds to hours
weekly['hours'] = (weekly['total_duration_ms'] / (1000 * 60 * 60)).round(2)




# 4. Top Album
top_album = pd.read_sql("""
    SELECT album, COUNT(*) AS play_count
    FROM spotify_history
    GROUP BY album
    ORDER BY play_count DESC
    LIMIT 1;
""", conn)

# 5. Latest Track
latest = pd.read_sql("""
    SELECT track_name, artist, album, played_at
    FROM spotify_history
    ORDER BY played_at DESC
    LIMIT 1;
""", conn)

conn.close()


# --- Streamlit UI ---
st.set_page_config(page_title="Spotify Listening Insights", layout="wide")
st.title("🎵 hi")

# --- Top Metrics ---
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("🕒 gigi")
    st.markdown(
        f"""
        <div style='font-size: 20px; font-weight: bold;'>{total_time_today}</div>
        """,
        unsafe_allow_html=True
    )

with col2:
    st.subheader("🎧 Latest Track")
    played_time = pd.to_datetime(latest['played_at'][0]).tz_localize('UTC').tz_convert('Asia/Singapore').strftime('%Y-%m-%d %H:%M')
    st.markdown(
        f"""
        <div style='font-size: 20px; font-weight: bold;'>{latest['track_name'][0]} &nbsp;
            <span style='color: gray; font-weight: normal; font-size: 16px;'>by <span style='font-weight: 600;'>{latest['artist'][0]}</span> @ {played_time}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

with col3:
    st.subheader("💿 Most Played Album")
    st.markdown(
        f"""
        <div style='font-size: 20px; font-weight: bold;'>{top_album['album'][0]} &nbsp;
            <span style='color: gray; font-weight: normal; font-size: 16px;'>({top_album['play_count'][0]} plays)</span>
        </div>
        """,
        unsafe_allow_html=True
    )

# --- Artist and Weekly Listening Trend ---
col1, col2 = st.columns(2)

with col1:
    # Create a mapping of rank to emoji
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]

    # Convert the DataFrame into a list of tuples: (medal, artist, count)
    ranked_artists = []
    for i, row in top_artists.iterrows():
        emoji = medals[i] if i < len(medals) else f"{i+1}."
        ranked_artists.append((emoji, row["artist"], row["play_count"]))
    
    st.subheader("🎤 Top 5 Artists (All Time)")
    for medal, artist, count in ranked_artists:
        st.markdown(
            f"<div style='font-size:28px;'>{medal} <strong>{artist}</strong> ({count} plays)</div>",
            unsafe_allow_html=True
        )

with col2:
    st.subheader("📈 Weekly Listening Trend")
    st.line_chart(weekly.set_index('date')['hours'])

# --- Footer with Playlist Link ---
st.markdown(
    """
    <div style='text-align: right; font-size: 0.85rem; margin-top: 30px; color: gray;'>
        <a href='https://open.spotify.com/user/darrenation?si=a094dca8596b4ad2' target='_blank' style='color: #1DB954;'>Visit my Spotify</a>
    </div>
    """,
    unsafe_allow_html=True
)
