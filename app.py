import urllib.request
import urllib.error
import urllib.parse
import json
import re
import os
import asyncio
import time
from datetime import datetime, timedelta, timezone
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_interval(name, default=24):
    env_value = os.getenv(name, "").strip()
    if env_value == "":
        return default
    if not env_value.isdigit():
        print(f"WARNING: Invalid {name} value: {env_value!r} (not a number), using default {default} hours.")
        return default
    return int(env_value)

def parse_bool(value):
    value = str(value)
    return value.lower() in ("true", "1", "yes")

WOWAUDIT_API_TOKEN = os.getenv("WOWAUDIT_API_TOKEN", None)
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 30))
DISABLE_LEGACY_RAIDS = parse_bool(os.getenv("DISABLE_LEGACY_RAIDS", 1))
UPDATE_INTERVAL_HOURS = timedelta(hours=get_interval("UPDATE_INTERVAL_HOURS", 24))
USER_AGENT = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
)

if WOWAUDIT_API_TOKEN is None:
    raise "ERROR: You have not set the WOWAUDIT_API_TOKEN. It is required to run the app. Please read the documentation: https://github.com/Deltachaos/wowaudit-auto-sims?tab=readme-ov-file#getting-a-wow-audit-api-token"

def http_request(method, url, headers=None, data=None):
    """
    Synchronously perform an HTTP request.
    Data (if provided) should be a string; it is encoded to bytes.
    """
    if data is not None:
        if isinstance(data, str):
            data = data.encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(req) as resp:
        resp_data = resp.read().decode('utf-8')
        return json.loads(resp_data)


async def async_http_request(method, url, headers=None, data=None):
    """
    Wrap the synchronous http_request in an asyncio thread.
    """
    return await asyncio.to_thread(http_request, method, url, headers, data)

async def get_team():
    url = "https://wowaudit.com/v1/team"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": WOWAUDIT_API_TOKEN
    }
    try:
        return await async_http_request("GET", url, headers)
    except Exception as e:
        print(f"Error fetching team: {e}")
        return None

async def get_region():
    data = await get_team()
    match = re.search(r"https://wowaudit\.com/([^/]+)/", data["url"])
    if match:
        return match.group(1)
    return None

async def get_latest_raid():
    url = "https://wowaudit.com/api/instances?kind=live"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": WOWAUDIT_API_TOKEN
    }
    try:
        data = await async_http_request("GET", url, headers)
        for raid in data:
            if raid["current"]:
                return raid

        return None
    except Exception as e:
        print(f"Error fetching team: {e}")
        return None

async def get_characters():
    """
    Retrieve the list of characters from the wowaudit API.
    """
    url = "https://wowaudit.com/v1/characters"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": WOWAUDIT_API_TOKEN
    }
    try:
        data = await async_http_request("GET", url, headers)
        return data
    except Exception as e:
        print(f"Error fetching characters: {e}")
        return []

def clear(text):
    return ''.join(char for char in text if char.isalnum()).lower()

def start_sim_with_browser(region, realm, char_name, raid, difficulty, sim, is_latest):
    """Starts a Raidbots simulation using a headless browser and returns the sim_id."""
    url = f"https://www.raidbots.com/simbot/droptimizer?region={region}&realm={realm}&name={char_name}"

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    print(f"Start sim for {region} {char_name}-{realm} for raid {raid} {difficulty} with settings: {sim}")
    driver = webdriver.Chrome(options=options)
    driver.get(url)

    def click(element):
        driver.execute_script("arguments[0].click();", element)
        return True

    def wait_for_char_loaded():
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_all_elements_located((By.XPATH, "//h3[contains(text(), 'Sources')]")))

    def find_item_with_text(selector, text):
        wait = WebDriverWait(driver, 10)
        elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector)))

        for element in elements:
            if clear(element.text) == clear(text):
                return element
        return None

    def set_checkbox(text, value):
        wait = WebDriverWait(driver, 10)
        labels = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "label")))

        # TODO check if checkbox is set currently
        for label in labels:
            if clear(label.text) == clear(text):
                return click(label)
        return False

    def set_item_level(value):
        label = find_item_with_text(".Text", "Upgrade up to:")
        script = """
            (function(text) {
              var input = text.nextElementSibling.querySelector('input');
              input.focus();
              input.dispatchEvent(new Event('focusin', { bubbles: true, cancelable: true }));
              input.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, cancelable: true, keyCode: 32 }));
            })(arguments[0])
        """
        driver.execute_script(script, label)

        latest_option = None
        options = []
        box = label.find_element(By.XPATH, "./..")
        for listbox in box.find_elements(By.CSS_SELECTOR, "[id$='listbox']"):
            for option in listbox.find_elements(By.CSS_SELECTOR, "[id*='option']"):
                options.append(option)
                latest_option = option

        if not options:
            print("no options found")
            return False

        if not latest_option:
            print("no latest_option found")
            return False
        
        if value == -1:
            print(f"Found latest option {latest_option.text}")
            return click(latest_option)

        for option in options:
            print(f"Found option {option.text}")
            match = re.search(r'(\d+)/\d+', clear(option.text))
            if match and match.group(1) == value:
                return click(option)

        return False

    def select_raid(raid_name):
        """Selects the specified raid from the list."""
        item = find_item_with_text("#instanceList .Box", raid_name)
        if item:
            return click(item)
        return False

    def select_difficulty(difficulty):
        """Selects the specified raid difficulty."""
        wait = WebDriverWait(driver, 10)

        headings = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".Heading")))
        for heading in headings:
            if clear(heading.text) == clear("raid difficulty"):
                box = heading.find_element(By.XPATH, "./..")
                difficulty_elements = box.find_elements(By.CSS_SELECTOR, ".Text:first-child")

                for element in difficulty_elements:
                    if clear(element.text) == clear(difficulty):
                        return click(element.find_element(By.XPATH, "./.."))
        return False

    def start_sim():
        """Clicks the 'Run Droptimizer' button to start the simulation."""
        item = find_item_with_text(".Button", "run droptimizer")
        if item:
            return click(item)
        return False

    wait_for_char_loaded()

    print("Show all raids")
    time.sleep(3)
    if not set_checkbox("Show Previous Tiers", True):
        raise "Could not show all raids"

    time.sleep(3)
    print("Select raid " + raid["name"])
    if not select_raid(raid["name"]):
        raise "Could not select raid"

    time.sleep(3)
    print("Select difficulty " + difficulty)
    if not select_difficulty(difficulty):
        raise "Could not select difficulty"

    print("Set match_equipped_gear to " + str(sim["match_equipped_gear"]))
    time.sleep(3)
    if not set_checkbox("Upgrade All Equipped Gear to the Same Level", sim["match_equipped_gear"]):
        raise "Could not select match_equipped_gear"

    time.sleep(3)
    level = sim["upgrade_level"]
    if not is_latest:
        level = -1
    print("Set item level to " + str(level))
    if not set_item_level(level):
        raise "Could not set item level"

    # TODO fight style, number of bosses, fight length

    #print("Set pi to " + str(sim["pi"]))
    #time.sleep(3)
    #if not set_checkbox("Power Infusion (beta)", sim["pi"]):
    #    raise "Could not select pi"

    old_url = driver.current_url

    time.sleep(3)
    print("Start sim")
    if not start_sim():
        raise "Could not start sim"

    while old_url == driver.current_url:
        time.sleep(1)

    sim_url = driver.current_url
    driver.quit()

    sim_id = sim_url.split("/")[-1]  # Extract sim_id from URL
    return sim_id

async def poll_sim(sim_id, character_name, raid, difficulty):
    """
    Poll the raidbots sim status periodically and print progress.
    Completion is determined when the response returns {"message": "No job found"}.
    """
    url = f"https://www.raidbots.com/api/job/{sim_id}"
    headers = {
        "Accept": "application/json",
        "User-Agent": USER_AGENT
    }
    while True:
        try:
            response = await async_http_request("GET", url, headers)
            # Check if the sim has completed.
            if isinstance(response, dict) and response.get("message") == "No job found":
                print(f"Sim {raid} {difficulty} {sim_id} for {character_name} completed.")
                break

            # If job details are available, print progress.
            if "job" in response:
                job = response["job"]
                state = job.get("state", "unknown")
                progress = job.get("progress", "unknown")
                total = "unknown"
                position = "unknown"
                if "queue" in response:
                    total = response["queue"].get("total", "unknown")
                    position = response["queue"].get("position", "unknown")
                print(
                    f"Sim {raid} {difficulty} {sim_id} for {character_name} is {state} (queue {position}/{total}) with progress {progress}")
                if state == "complete":
                    break
            else:
                print(f"Sim {raid} {difficulty} {sim_id} for {character_name} progress: {response}")

        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"Sim {raid} {difficulty} {sim_id} for {character_name} completed.")
                break
            else:
                print(f"Unexpected HTTP error for sim {raid} {difficulty} {sim_id}: {e}")

        await asyncio.sleep(POLL_INTERVAL)


async def upload_wishlist(character, report_id):
    """
    Upload the wishlist to wowaudit after sim completion.
    """
    url = "https://wowaudit.com/v1/wishlists"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": WOWAUDIT_API_TOKEN
    }
    payload = {
        "report_id": report_id,
        "character_id": character["id"],
        "character_name": character["name"],
        "configuration_name": "Single Target",
        "replace_manual_edits": True,
        "clear_conduits": True
    }
    data_str = json.dumps(payload)
    try:
        response = await async_http_request("POST", url, headers, data_str)
        print(f"Wishlist uploaded for {character['name']}-{character['realm']}: {response}")
    except Exception as e:
        print(f"Error uploading wishlist {report_id} for {character['name']}-{character['realm']}: {e}")

async def get_wishlists():
    url = "https://wowaudit.com/v1/wishlists"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": WOWAUDIT_API_TOKEN
    }
    try:
        return await async_http_request("GET", url, headers)
    except Exception as e:
        print(f"Error fetching wishlists: {e}")


def get_latest_date(data):
    latest_key = None
    latest_date = None

    for key, date_str in data.items():
        if date_str:
            date_obj = datetime.fromisoformat(date_str[:-6]).replace(tzinfo=timezone.utc)
            if latest_date is None or date_obj > latest_date:
                latest_key, latest_date = key, date_obj

    return (latest_key, latest_date) if latest_key else None

def is_newer_than_two_days(latest_entry):
    if not latest_entry:
        return False

    _, latest_date = latest_entry
    return latest_date > datetime.now(timezone.utc) - UPDATE_INTERVAL_HOURS

def is_already_updated(dates):
    latest = get_latest_date(dates)
    if latest is None:
        return False
    return is_newer_than_two_days(latest)

async def process_raidbots_character(region, character, latest, raids, sim_map, latest_updates):
    """
    Process a single character:
      - Fetch gear from raidbots.
      - Start a sim.
      - Poll until the sim is complete.
      - Upload the wishlist to wowaudit.
    """
    name = character["name"]
    realm = character["realm"]
    character_name = f"{name}-{realm}"
    print(f"Processing character: {character_name}")

    for raid in raids:
        raid_name = raid["name"]
        is_latest = latest["id"] == raid["id"]
        if DISABLE_LEGACY_RAIDS and not is_latest:
            print(f"Skip {raid_name} because legacy raids are skipped")
            continue
        
        for difficulty, sims in sim_map.items():
            if character["id"] in latest_updates and raid["id"] in latest_updates[character["id"]] and difficulty in latest_updates[character["id"]][raid["id"]] and is_already_updated(latest_updates[character["id"]][raid["id"]][difficulty]):
                print(f"Skip {raid_name} {difficulty} because its updated already")
                continue

            for sim in sims:
                sim_id = start_sim_with_browser(region, realm, name, raid, difficulty, sim, is_latest)
                if not sim_id:
                    print(f"Sim {raid_name} {difficulty} response for {character_name} missing simId.")
                    continue

                print(f"Sim {raid_name} {difficulty} started for {character_name}, sim_id: {sim_id}")
                await poll_sim(sim_id, character_name, raid_name, difficulty)
                await upload_wishlist(character, sim_id)


def get_raids(wishlists):
    for character in wishlists["characters"]:
        instances = []
        for instance in character["instances"]:
            instances.append({
                "id": instance["id"],
                "name": instance["name"]
            })
        return instances

    return None

def get_difficulties(wishlists):
    for character in wishlists["characters"]:
        for instance in character["instances"]:
            difficulties = []
            for difficulty in instance["difficulties"]:
                difficulties.append(difficulty["difficulty"])
            return difficulties

    return None


def get_latest_updates(wishlists):
    updates = {}
    for character in wishlists["characters"]:
        updates[character["id"]] = {}
        for instance in character["instances"]:
            updates[character["id"]][instance["id"]] = {}
            for difficulty in instance["difficulties"]:
                updates[character["id"]][instance["id"]][difficulty["difficulty"]] = difficulty["wishlist"][
                    "updated_at"]

    return updates

def get_droptimizer_settings(difficulties):
    default_settings = {
        "fight_duration": 5,
        "fight_style": "Patchwerk",
        "match_equipped_gear": False,
        "number_of_bosses": 1,
        "pi": False,
        "sockets": False,
        "upgrade_level": {level: 0 for level in difficulties}
    }

    settings = []
    indexed_settings = {}
    pattern = re.compile(r"DROPTIMIZER_(\d+)_(.*)")

    for key, value in os.environ.items():
        match = pattern.match(key)
        if match:
            index, setting_name = match.groups()
            setting_name = setting_name.lower()
            index = int(index)

            if index not in indexed_settings:
                indexed_settings[index] = default_settings.copy()
                indexed_settings[index]["upgrade_level"] = default_settings["upgrade_level"].copy()

            if setting_name in indexed_settings[index]:
                if isinstance(default_settings[setting_name], bool):
                    indexed_settings[index][setting_name] = parse_bool(value)
                elif isinstance(default_settings[setting_name], int):
                    indexed_settings[index][setting_name] = int(value)
                else:
                    indexed_settings[index][setting_name] = value
            elif setting_name.startswith("upgrade_level_"):
                setting_upgrade_level = setting_name.removeprefix("upgrade_level_")
                if setting_upgrade_level in indexed_settings[index]["upgrade_level"]:
                    indexed_settings[index]["upgrade_level"][setting_upgrade_level] = int(value)

    for index in sorted(indexed_settings.keys()):
        settings.append(indexed_settings[index])

    if not settings:
        settings = [default_settings]

    return settings


def transform_settings(difficulties, settings):
    transformed = {level: [] for level in difficulties}

    for entry in settings:
        base_entry = {k: v for k, v in entry.items() if k != "upgrade_level"}
        for key, value in entry["upgrade_level"].items():
            new_entry = base_entry.copy()
            new_entry["upgrade_level"] = value
            transformed[key].append(new_entry)

    return transformed

def get_sims(difficulties):
    settings = get_droptimizer_settings(difficulties)
    return transform_settings(difficulties, settings)

async def main():
    """
    Main function: fetch all characters and start processing them concurrently.
    """
    region = await get_region()
    if not region:
        raise "No region found"

    wishlists = await get_wishlists()
    if not wishlists:
        raise "No wishlists found"

    raids = get_raids(wishlists)
    if not raids:
        raise "No raids found"

    difficulties = get_difficulties(wishlists)
    if not difficulties:
        print("No difficulties to process.")
        return

    sims = get_sims(difficulties)
    if not sims:
        print("No sims to process.")
        return

    print(sims)

    latest_updates = get_latest_updates(wishlists)

    print(f"Run for region {region}")

    characters = await get_characters()
    if not characters:
        print("No characters to process.")
        return

    latest_raid = await get_latest_raid()
    if not latest_raid:
        print("No latest raid found.")
        return

    # Create a task for each character.
    tasks = [asyncio.create_task(process_raidbots_character(region, character, latest_raid, raids, sims, latest_updates)) for character in characters if character["role"] != "Heal"]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
