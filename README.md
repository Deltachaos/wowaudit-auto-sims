# WoW Audit Auto Sims

## Overview
This project automates the process of running Raidbots simulations for World of Warcraft characters and uploads the results to WoW Audit. It utilizes Selenium to navigate Raidbots' web interface, starts simulations, polls for completion, and updates WoW Audit with the best gear wishlist.

## Supporting the Community
We want to take a moment to appreciate the amazing work done by [WoW Audit](https://wowaudit.com/), [Raidbots](https://www.raidbots.com/) and [SimulationCraft](https://www.simulationcraft.org/). These tools provide invaluable resources for optimizing your World of Warcraft characters.

If you find these tools helpful, consider supporting them by subscribing to their [WoW Audit Patreon](https://www.patreon.com/auditspreadsheet), [Raidbots Premium](https://www.raidbots.com/). Your support helps them continue improving and maintaining these great services for the WoW community!

## Features
- Fetches character and raid information from WoW Audit.
- Starts Raidbots Droptimizer simulations via a headless browser.
- Polls the simulation job status until completion.
- Uploads the generated wishlist to WoW Audit.
- Processes multiple characters asynchronously.
- The script currently processes only non-healer characters.

## Requirements
- Python 3.8+
- Google Chrome or Firefox
- Required Python packages (see `requirements.txt`)
- WoW Audit API token (set as an environment variable `WOWAUDIT_API_TOKEN`)

## Configuration
The script supports the following environment variables for configuration:

- `WOWAUDIT_API_TOKEN`: Your WoW Audit API token.
- `UPDATE_INTERVAL_HOURS`: The interval (in hours) at which character data is updated, if its outdated. Default: `24`.
- `POLL_INTERVAL`: The interval (in seconds) at which the script polls for simulation completion. Default: `30`.
- `USER_AGENT`: The user agent string used for web requests. Default: `Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36`.
- `DISABLE_LEGACY_RAIDS`: Disalbes sim for non recent raids. Default: `1`.

## Getting a WoW Audit API Token
To use this script, you need to obtain a WoW Audit API token:
1. Go to [WoW Audit](https://wowaudit.com/).
2. Log in with your account.
3. Navigate to the API settings section.
4. Generate a new API token and copy it.
5. Set the token as an environment variable `WOWAUDIT_API_TOKEN` on your system.

## Installation
You can also run the script on [Github Actions](https://github.com/Deltachaos/wowaudit-auto-sims?tab=readme-ov-file#running-the-job-on-github-ci).

1. Clone the repository:
   ```sh
   git clone https://github.com/Deltachaos/wowaudit-auto-sims.git
   cd wowaudit-auto-sims
   ```
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
3. Ensure Google Chrome and ChromeDriver are installed and accessible in your system path.

## Usage
1. Set up your environment variables:
   ```sh
   export WOWAUDIT_API_TOKEN="your_api_token_here"
   export UPDATE_INTERVAL_HOURS=24
   export POLL_INTERVAL=30
   export USER_AGENT="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
   ```
2. Run the script:
   ```sh
   python main.py
   ```
3. The script will automatically fetch characters, initiate simulations, monitor their progress, and upload results.

### Droptimizer Simulation Settings
The script also supports the following environment variables, prefixed with `DROPTIMIZER_`, to configure Droptimizer simulations. These settings are indexed (e.g., `DROPTIMIZER_0_FIGHT_DURATION`, `DROPTIMIZER_1_FIGHT_DURATION`, etc.).

The stroked settings are currently not implemented, but planned.

- `DROPTIMIZER_X_FIGHT_DURATION`: Fight duration in seconds. Default: `300`.
- `DROPTIMIZER_X_FIGHT_STYLE`: The fight style to simulate (e.g., `Patchwerk`). Default: `Patchwerk`.
- - Patchwerk
- - DungeonSlice,
- - TargetDummy
- - ExecutePatchwerk
- - HecticAndCleave
- - LightMovement
- - HeavyMovement
- - CastingPatchwerk
- - CleaveAdd
- `DROPTIMIZER_X_MATCH_EQUIPPED_GEAR`: Whether to match currently equipped gear. Default: `False`.
- `DROPTIMIZER_X_NUMBER_OF_BOSSES`: Number of bosses in the encounter. Default: `1`.
- `DROPTIMIZER_X_PI`: Whether Power Infusion (PI) is considered. Default: `False`.
- ~~`DROPTIMIZER_X_SOCKETS`: Whether to prioritize socketed items. Default: `False`.~~
- `DROPTIMIZER_TALENTS_CLASS_SPEC`: Overwrite the talent string for specific classes and specs. Default: Current used talents.
- - `CLASS` is the english class name without spaces uppercase. Example: `DEMONHUNTER`
- - `SPEC` is the english spec name without spaces uppercase. Example: `HAVOC`
- - The value is the talent string from wowhead talent calculator: Example: `CEkAAAAAAAAAAAAAAAAAAAAAAYGMzMzYMzMjZmJmZGAAAAAAwsZMbzwMzsNzMbWmlxwMzwYZbWmBDjtNmkhZmBWWA`

#### Upgrade Levels

The Upgrade Levels can be set to:

- `-1`: Always select the maximum
- `0`: Base level, no upgrades
- `1`, `2`, `3`, ...: The upgrade level, like Champion 1/8

Settings:

- `DROPTIMIZER_X_UPGRADE_LEVEL_HEROIC`: Heroic upgrade level. Default: `0`.
- `DROPTIMIZER_X_UPGRADE_LEVEL_NORMAL`: Normal upgrade level. Default: `0`.
- `DROPTIMIZER_X_UPGRADE_LEVEL_MYTHIC`: Mythic upgrade level. Default: `0`.
- `DROPTIMIZER_X_UPGRADE_LEVEL_RAID_FINDER`: Raid Finder upgrade level. Default: `0`.

## Running the Job on GitHub CI

**ATTENTION: YOU DONT HAVE TO FORK THE REPOSITORY. The Github CI file will check out a this repostory automatically**

You can run this project as a scheduled GitHub Action in a private repository. Use the following GitHub CI workflow:

Create a `.github/workflows/ci.yml` file in your repository and add the following content:

```yaml
name: Update WoW Audit

on:
  push:
    branches:
      - main
  schedule:
    - cron: "45 17 * * *"

permissions:
  actions: write

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v3
        with:
          repository: "Deltachaos/wowaudit-auto-sims"
          ref: "main"
          path: "app"
          
      - name: Install dependencies
        run: |
          sudo apt-get update -qq
          sudo apt-get install -y firefox xvfb

      - name: Install project dependencies
        run: |
          pip install -r app/requirements.txt

      - name: Run the application
        env:
          WOWAUDIT_API_TOKEN: ${{ secrets.WOWAUDIT_API_TOKEN }}
          UPDATE_INTERVAL_HOURS: ${{ vars.UPDATE_INTERVAL_HOURS }}
          DROPTIMIZER_0_FIGHT_DURATION: 300 # And other settings like described above 
        run: |
          xvfb-run --auto-servernum python3 app/app.py
```

### Setting Up Environment Variables in GitHub
1. **Secrets:**
   - Go to your GitHub repository settings.
   - Navigate to `Secrets and variables > Actions`.
   - Click `New repository secret` and add:
     - `WOWAUDIT_API_TOKEN`: Your WoW Audit API token.

2. **Variables:**
   - In the same section, navigate to `Variables`.
   - Click `New repository variable` and add:
     - `UPDATE_INTERVAL_HOURS`: Set this to your desired interval (default is `24`).

Once configured, GitHub Actions will run the script automatically on every push to `main` and at the scheduled time (`17:45 UTC` daily).

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributions
Contributions and pull requests are welcome! Feel free to open an issue or suggest improvements.

## Disclaimer
This project is not affiliated with Raidbots or WoW Audit. Use at your own risk.
