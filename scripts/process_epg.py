import gzip
import os
import re
import xml.etree.ElementTree as ET
import requests

M3U_URL = os.getenv("M3U_URL")
SOURCE_EPG_URL = os.getenv("SOURCE_EPG_URL")
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
  m3u_resp = requests.get(M3U_URL, timeout=30)
  m3u_text = m3u_resp.text
  with open("output/playlist.m3u", "w", encoding="utf-8") as f:
    f.write(m3u_text)

  active_ids = get_active_tvg_ids(m3u_text)
  print(f"Found {len(active_ids)} unique tvg-ids in M3U.")

  # Create root structure for output XMLTV
  root = ET.Element("tv")

  existing_channels = set()

  print("Processing primary Source EPG...")
  primary_resp = requests.get(SOURCE_EPG_URL, timeout=60)
  primary_root = ET.fromstring(primary_resp.content)

  # Add primary channels
  for channel in primary_root.findall("channel"):
    ch_id = channel.get("id")
    if ch_id:
      existing_channels.add(ch_id)
      root.append(channel)

  # Add primary programmes only for channels present in your M3U
  for prog in primary_root.findall("programme"):
    if prog.get("channel") in active_ids:
      root.append(prog)

  # Clear memory
  del primary_root

  # Process secondary epg.guru URLs iteratively to save memory
  for idx, guru_url in enumerate(EPG_GURU_URLS, start=1):
    print(f"Streaming and processing epg.guru source #{idx}: {guru_url}")
    try:
      resp = requests.get(guru_url, timeout=60, stream=True)
      # Parse XML iteratively using iterparse
      for event, elem in ET.iterparse(resp.raw, events=("end",)):
        if elem.tag == "channel":
          ch_id = elem.get("id")
          if ch_id and ch_id not in existing_channels:
            existing_channels.add(ch_id)
            root.append(elem)
          else:
            elem.clear()
        elif elem.tag == "programme":
          ch_id = elem.get("channel")
          if ch_id in active_ids:
            root.append(elem)
          else:
            elem.clear()
    except Exception as e:
      print(f"Failed to process {guru_url}: {e}")

  print("Building final XML output...")
  tree = ET.ElementTree(root)
  # Write to bytes buffer first
  xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)

  print("Writing and compressing files...")
  with open("output/epg.xml", "wb") as f:
    f.write(xml_bytes)

  with gzip.open("output/epg.xml.gz", "wb") as f:
    f.write(xml_bytes)

  print("Merge complete!")


if __name__ == "__main__":
  merge_xmltv()
