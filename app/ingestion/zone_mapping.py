"""
IMD identifies locations by numeric district "Obj_ID"s and short station
call signs — there is no public "list all IDs" endpoint in IMD's API
reference docs, so this file can't ship with verified real IDs for your
specific NER zones. It ships with placeholders instead of guessed numbers,
because a wrong-but-plausible-looking ID silently pulls another location's
weather data with no error — worse than an obvious placeholder that fails
loudly.

How to find the real values for each zone:

- **station_id** (for get_current_weather / "Last 24 hrs Rainfall"):
  Open https://city.imd.gov.in, search for the nearest city/station, and
  check the network requests your browser makes (or the page URL) for a
  station code — IMD's docs show "NDL" for New Delhi Lodi Road as an
  example. Match each zone to its nearest IMD station.

- **district_obj_id** (for get_district_rainfall / get_district_warning):
  Open https://mausam.imd.gov.in/responsive/rainfallinformation.php or
  https://mausam.imd.gov.in/responsive/districtWiseWarningGIS.php, select
  your state and district from the dropdowns, and check the network
  request for the "id" / "Obj_ID" parameter used. IMD's docs show "164"
  for Adilabad as an example format.

Replace the "REPLACE_ME" placeholders below once you have real values —
ingest_rainfall_and_warnings() skips any zone still marked that way rather
than silently calling a wrong ID.
"""

ZONE_TO_IMD = {
    "Sector 01": {"station_id": "REPLACE_ME", "district_obj_id": "REPLACE_ME"},  # Guwahati
    "Sector 02": {"station_id": "REPLACE_ME", "district_obj_id": "REPLACE_ME"},  # Shillong
    "Sector 03": {"station_id": "REPLACE_ME", "district_obj_id": "REPLACE_ME"},  # Itanagar
    "Sector 04": {"station_id": "REPLACE_ME", "district_obj_id": "REPLACE_ME"},  # Kohima
    "Sector 05": {"station_id": "REPLACE_ME", "district_obj_id": "REPLACE_ME"},  # Imphal
    "Sector 06": {"station_id": "REPLACE_ME", "district_obj_id": "REPLACE_ME"},  # Aizawl
    "Sector 07": {"station_id": "REPLACE_ME", "district_obj_id": "REPLACE_ME"},  # Aizawl outskirts
    "Sector 08": {"station_id": "REPLACE_ME", "district_obj_id": "REPLACE_ME"},  # Gangtok
}


def is_configured(zone_name: str) -> bool:
    mapping = ZONE_TO_IMD.get(zone_name)
    if not mapping:
        return False
    return mapping["station_id"] != "REPLACE_ME" and mapping["district_obj_id"] != "REPLACE_ME"
