![Banner](https://codehs.com/uploads/62ebc28cf290a5af5f30c9a705221c93)

Do you have a decrypted gameDB that has lots of customization but also want a gameDB from a car model mod that includes slots that aren't in your main? This tool will merge that mod DB into your main DB so you can enjoy both at once!

## ✨ Features
* **Intelligent Merging:** Syncs tables between source (mod) and target (game) databases using robust `INSERT OR REPLACE` logic.
* **Automated Backups:** Generates a `.bak` snapshot before every operation—never lose your progress.
* **Quick Merge Library:** Save custom configurations and favorite file paths for one-click execution.
* **Integrated Restore:** Roll back to previous database states directly from the **Backup History** dashboard.
* **Modern UI:** Optimized for Windows 10/11 with DPI awareness, rounded corners, and a sleek dark theme.

---

## 🛠️ Requirements
* **OS:** Windows 10 or 11.
* **Environment:** Python 3.10+ (if running from source).
* **Data State:** Databases must be **decrypted** and share identical table schemas.

---

## 🚀 Setup & Usage
1.  **Launch:** Run `Varsinity's DB Merger.exe`.
2.  **Select Targets:**
    * **Target Database:** The main game file you want to update.
    * **Source Database:** The mod/donor file containing the new data.
3.  **Execute:** Click **Execute Database Merge**.
4.  **Verify:** Check the **Operation Log** for real-time status updates.
5.  **Success:** Launch the game! It will update your main DB.

---

## 💾 Backup & Safety
The tool automatically creates a backup in the target directory:
`TargetDatabase_YYYYMMDD_HHMMSS.bak`

If the schema is mismatched or a conflict occurs, your original data remains safe. You can manage or delete these snapshots within the **Backup History** tab.

---

## ⚠️ Important Notes
* **Schema Matching:** Because the tool uses `SELECT *`, the source and target tables must have the exact same columns and order.
* **Session Memory:** The application automatically remembers your last used database and favorite configurations.
* **File Access:** Ensure the game is closed before merging to avoid "File in use" errors.

---

## ⚖️ Copyright & Distribution
This repository and its contents are provided for use only via the official source. Redistribution or sharing of the binaries outside of this GitHub repository is not authorized.
