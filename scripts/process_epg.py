import gzip
import os
import re
import xml.etree.ElementTree as ET
import requests

M3U_URL = os.getenv("M3U_URL")
SOURCE_EPG_URL = os.getenv("SOURCE_EPG_URL")
# Supports comma-separated URLs
EPG_GURU_URLS = [
    url.strip()
    for url in os.getenv("EPG_GURU_URLS", "").split(",")
    if url.strip()
]

os.makedirs("output", exist_ok=True)


def get_active_tvg_ids(m3u_content):
  """Extract all tvg-id values from the M3U playlist."""
  ids = set()
  for line in m3u_content.splitlines():
    if line.startswith("#EXTINF"):
      match = re.search(r'tvg-id="([^"]+)"', line)
      if match and match.group(1):
        ids.add(match.group(1))
  return ids


def merge_xmltv():
  print("Downloading M3U...")
  m3u_resp = requests.get(M3U_URL)
  m3u_text = m3u_resp.text
  with open("output/playlist.m3u", "w", encoding="utf-8") as f:
    f.write(m3u_text)

  active_ids = get_active_tvg_ids(m3u_text)
  print(f"Found {len(active_ids)} unique tvg-ids in M3U.")

  print("Downloading primary Source EPG...")
  primary_resp = requests.get(SOURCE_EPG_URL)
  primary_tree = ET.fromstring(primary_resp.content)

  # Track channels and programs already present
  existing_channels = set()
  for channel in primary_tree.findall("channel"):
    ch_id = channel.get("id")
    if ch_id:
      existing_channels.add(ch_id)

  # Fetch and merge secondary epg.guru XMLs
  for idx, guru_url in enumerate(EPG_GURU_URLS, start=1):
    print(f"Fetching epg.guru source #{idx}: {guru_url}")
    try:
      resp = requests.get(guru_url, timeout=30)
      guru_tree = ET.fromstring(resp.content)

      # Merge new channels
      for channel in guru_tree.findall("channel"):
        ch_id = channel.get("id")
        if ch_id and ch_id not in existing_channels:
          primary_tree.append(channel)
          existing_channels.add(ch_id)

      # Merge programmes for existing or newly added channels
      for prog in guru_tree.findall("programme"):
        ch_id = prog.get("channel")
        # Optional: verify if program belongs to active channels in your M3U
        if ch_id in existing_channels:
          primary_tree.append(prog)

    except Exception as e:
      print(f"Failed to process {guru_url}: {e}")

  # Write output XML
  merged_data = ET.tostring(primary_tree, encoding="utf-8", xml_declaration=True)

  with open("output/epg.xml", "wb") as f:
    f.write(merged_data)

  # Compress to .xml.gz (Best practice for client players)
  with gzip.open("output/epg.xml.gz", "wb") as f:
    f.write(merged_data)

  print("EPG Merge and compression complete!")


if __name__ == "__main__":
  merge_xmltv()
