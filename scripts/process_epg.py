import gzip
import os
import xml.etree.ElementTree as ET
import requests

M3U_URL = os.getenv("M3U_URL")
EPG_GURU_URL = os.getenv("EPG_GURU_URL")

os.makedirs("output", exist_ok=True)


def update_guide():
  # Fetch M3U
  m3u_response = requests.get(M3U_URL)
  with open("output/playlist.m3u", "wb") as f:
    f.write(m3u_response.content)

  # Fetch EPG from epg.guru
  epg_response = requests.get(EPG_GURU_URL)

  # Write uncompressed XML
  with open("output/epg.xml", "wb") as f:
    f.write(epg_response.content)

  # Compress to .gz to save bandwidth & bypass GitHub file warnings
  with gzip.open("output/epg.xml.gz", "wb") as f:
    f.write(epg_response.content)


if __name__ == "__main__":
  update_guide()
