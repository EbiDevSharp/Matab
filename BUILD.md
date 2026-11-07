# MatabDesk 1.2.0

Independent Android host and loopback-only Python desktop server share the bundled Persian UI. State schema 5; Android SQLite schema 3; APK code 3. Local SQLite keeps catalogs, customer registry, service/payment snapshots, material receipts/consumption, append-only activity history and release notes.

## Run and check

Python 3.10+ with sqlite3 and zoneinfo, and Node for model tests:

```
python3 desktop/server.py
node tests/model.cjs
node tests/finance.cjs
node tests/profiles-backup.cjs
node tests/money.cjs
python3 -m unittest discover -s tests -p 'test_*.py'
```

Run model scripts first to regenerate synthetic fixtures. Calendar checks cover 73,414 valid Persian dates in years 1300–1500. Python tests cover both previous SQLite schema upgrades, restart roundtrip, stale writers, atomic rejects, audit filtering (including Tehran local hours), history import/deduplication, backup scopes and HTTP boundaries.

The Windows bundle includes official Python 3.13.9 x64 embeddable runtime and its license. `timezone-Tehran.tzif` supplies Tehran timezone data without requiring an external tzdata package. The desktop default path remains `%LOCALAPPDATA%/MatabDesk/matab.sqlite3`.

## Android

Use Java, official Android platform 35 revision 2 and build-tools 35.0.0, plus Eclipse ECJ 3.39.0. Set `ANDROID_BUILD_TOOLS`, `ANDROID_JAR`, `ECJ_JAR`, then:

```
python3 android/build.py
```

The build recursively bundles web assets and fonts, compiles, converts with D8, aligns and signs the APK. Keep the existing private `signing/` key/password for in-place updates. Never publish signing material. Minimum Android 8/API26, target35. No INTERNET or broad storage permission. SAF handles import and export through installed file providers, including Google Drive when available.

`tests/FinanceValidatorTest.java` and `tests/ProfileValidatorTest.java` run native validator parity on the JVM with org.json 20240303, independently of Android runtime stubs. Device SQLite migration, SAF, print, rotation and vendor-specific WebView behavior still require target-device acceptance.

## State, money and history

`base-model.js` retains catalog validation, `finance-model.js` retains the previous financial schema, and `model.js` adds profiles/appearance/doctor/percentage validation. Earlier state versions migrate without guessing first/last-name splits. Divisor snapshots and unknown historical fees remain intact. Catalog rename never rewrites historical service labels.

Quantities are thousandths, percentages basis points and currency integer toman. Products/fees/shares use exact integer ratios (JS BigInt, Python integers, Java BigInteger). Per-lot cumulative rounding reconciles full consumed cost. Shares use customer payments, not gateway remittances. Percentage and divisor modes are snapshotted per service; clinic share is the remainder after doctor share. Reviewed consumption and known fees are required for an eligible share. Negative shares may occur on partial payment.

Activity writes occur in the same transaction as the successful state write. No-op saves do not create false edits. Logs retain entity labels and changed field names, not full before/after snapshots, and do not provide undo or operator identity. Restore keeps local activity and imports history with unique source keys and imported markers. Repeated imports are deduplicated. Timestamps depend on the device clock; filters/display use Tehran timezone. Release notes are seeded from `releases.json` into `app_releases`.

Full JSON backups include domain state, audit history and release notes; settings backups exclude services, patients and inventory. Settings restore merges catalog identities and retains old referenced entries inactive. Ambiguous name/ID collisions are rejected. Full restore replaces domain data and is not multi-device record merging. JSON is unencrypted and capped at 20 MiB, imported history at 100,000 entries; oversized backups require offline SQLite file copying after shutdown.

Drive support is file-provider/synced-folder based, not direct OAuth/API integration or background synchronization. Android uses ACTION_CREATE_DOCUMENT / ACTION_OPEN_DOCUMENT; Windows Chrome/Edge uses a user-selected save-file handle with download fallback. The user chooses the Drive location. Cloud upload completion cannot be asserted by the app. No Google credentials are embedded.

## Access and distribution

Desktop binds only 127.0.0.1, validates Host/Origin/Sec-Fetch-Site and requires a per-launch API token. SQLite access is protected by the OS account/device boundary. There is no network multi-user server, cloud sync, authentication or medical dosage advice.

Distribute clean source files, README/guide/licenses, calendar data, release notes and timezone data. Windows additionally includes runtime/. Source privately includes signing/. Exclude build/, deliverables/, test databases, caches, qa-* pages, .openai/ and preview package.json. No patient or synthetic QA database is distributed.

Physical Android installation, Windows execution and a real Google Drive account were not available for acceptance here. Browser checks use the same UI against the Linux SQLite backend.

## Version 1.3.0: clinic isolation

The original `matab.sqlite3` remains the `main` clinic. A separate `clinics.sqlite3` registry stores opaque clinic IDs and names; new clinic files are `clinic-<id>.sqlite3` in the same data directory. State schema 5 and per-clinic domain storage remain compatible. Android SQLite schema stays 4; the registry is managed separately.

Each page captures its clinic ID from the URL once. Desktop requests carry `X-Matab-Clinic`, resolved against the registry; native requests use `ClinicManager.request(id, action, payload)`. Unknown scope fails closed. No globally active bank is switched, so independent windows cannot redirect each other's writes. Per-clinic revision checks remain active. New clinics start with fresh defaults and no patient/service/inventory data; the original bank is never moved or rewritten for registry setup.

Registry listing derives current display names from initialized clinic state, so clinic renames/restores stay visible. JSON backup and restore target the active clinic only; the UI names the restore destination. There is no all-clinics archive, cross-clinic merger, shared doctor inventory or combined report in this version. For offline file-level backup, close the app and copy the entire data directory including the registry and all clinic DB files.

Tests: `test_clinics.py` and HTTP scope tests verify independent state, restore/export history isolation, original data preservation, unknown IDs, duplicate creation and reopen. Physical Android/Windows acceptance is still required.
