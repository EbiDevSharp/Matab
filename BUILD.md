# MatabDesk 1.4.0

Independent Android host and loopback-only Python desktop server share the bundled Persian UI. State schema 5; legacy Android SQLite schema 4; APK code 8. Local SQLite keeps catalogs, customer registry, service/payment snapshots, material receipts/consumption, append-only activity history and release notes.

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

The Windows bundle includes official Python 3.13.9 x64 embeddable runtime and its license. `timezone-Tehran.tzif` supplies Tehran timezone data without requiring an external tzdata package. The active desktop database is `%LOCALAPPDATA%/MatabDesk/matab-unified.sqlite3`; legacy files are retained after migration.

## Android

Use Java, official Android platform 35 revision 2 and build-tools 35.0.0, plus Eclipse ECJ 3.39.0. Set `ANDROID_BUILD_TOOLS`, `ANDROID_JAR`, `ECJ_JAR`, then:

```
python3 android/build.py
```

The build recursively bundles web assets and fonts, compiles, converts with D8, aligns and signs the APK. Keep the existing private `signing/` key/password for in-place updates. Never publish signing material. Minimum Android 8/API26, target35. No INTERNET or broad storage permission. SAF handles import and export through installed file providers, including Google Drive when available.

`tests/FinanceValidatorTest.java` and `tests/ProfileValidatorTest.java` run native validator parity on the JVM with org.json 20240303, independently of Android runtime stubs. Device SQLite migration, SAF, print, rotation and vendor-specific WebView behavior still require target-device acceptance.

## State, money and history

`base-model.js` retains catalog validation, `finance-model.js` retains the previous financial schema, and `model.js` adds profiles/appearance/doctor/percentage validation. Earlier state versions migrate without guessing first/last-name splits. Divisor snapshots and unknown historical fees remain intact. Catalog rename never rewrites historical service labels.

Quantities are thousandths, percentages basis points and currency integer toman. Products/fees/shares use exact integer ratios (JS BigInt, Python integers, Java BigInteger). Per-lot cumulative rounding reconciles full consumed cost. Shares use customer payments, not gateway remittances. Percentage is snapshotted per service; the UI migrates legacy divisors to percentage; clinic share is the remainder after doctor share. Reviewed consumption and known fees are required for an eligible share. Negative shares may occur on partial payment.

Activity writes occur in the same transaction as the successful state write. No-op saves do not create false edits. New logs retain entity labels, changed field names and full before/after snapshots; older logs retain only originally stored details. No undo or operator identity is provided. Restore keeps local activity and imports history with unique source keys and imported markers. Repeated imports are deduplicated. Timestamps depend on the device clock; filters/display use Tehran timezone. Release notes are seeded from `releases.json` into `app_releases`.

Full JSON backups include domain state, audit history and release notes; settings backups exclude services, patients and inventory. Settings restore merges catalog identities and retains old referenced entries inactive. Ambiguous name/ID collisions are rejected. Full restore replaces domain data and is not multi-device record merging. JSON is unencrypted and capped at 20 MiB, imported history at 100,000 entries; oversized backups require offline SQLite file copying after shutdown.

Drive support is file-provider/synced-folder based, not direct OAuth/API integration or background synchronization. Android uses ACTION_CREATE_DOCUMENT / ACTION_OPEN_DOCUMENT; Windows Chrome/Edge uses a user-selected save-file handle with download fallback. The user chooses the Drive location. Cloud upload completion cannot be asserted by the app. No Google credentials are embedded.

## Access and distribution

Desktop binds only 127.0.0.1, validates Host/Origin/Sec-Fetch-Site and requires a per-launch API token. SQLite access is protected by the OS account/device boundary. There is no network multi-user server, cloud sync, authentication or medical dosage advice.

Distribute clean source files, README/guide/licenses, calendar data, release notes and timezone data. Windows additionally includes runtime/. Source privately includes signing/. Exclude build/, deliverables/, test databases, caches, qa-* pages, .openai/ and preview package.json. No patient or synthetic QA database is distributed.

Physical Android installation, Windows execution and a real Google Drive account were not available for acceptance here. Browser checks use the same UI against the Linux SQLite backend.

## Version 1.4.0: unified clinic storage

Python Clinics and Android ClinicManager use one matab-unified.sqlite3 file. Clinics stores private domain JSON and revisions by clinic ID; shared_catalogs stores the services/products/areas/methods reference lists. activity_log is scoped by clinic_id, with '*' for shared reference changes. Doctors, patient registries, receipts, service/payment/consumption snapshots and settings remain clinic-specific. This is local separation, not access control or multiuser authentication.

First launch transactionally imports the legacy main bank and registry-linked banks; legacy_clinics.py remains solely for migration. Original files remain available as fallback archives, never active after the marker commits. Matching normalized reference names merge, conflicting IDs with different names are remapped, and historical labels, payment fees and receipt costs remain snapshots. Any global reference change increments every clinic revision to fence stale windows.

Full/settings backup formats remain compatible. Restore adds missing shared options while retaining existing shared defaults; all-clinic restore adds fresh clinic IDs and suffixes duplicate names. Backup-all uses one SQLite read transaction; restore-all commits the entire collection in one transaction. Limits: 100 clinics, 1,000 entries per shared catalog, 20 MiB JSON backup, 100,000 imported history rows per clinic.

New audit events contain before/after JSON snapshots. Rows open a detail dialog; historical events without snapshots explicitly say so. No undo is provided. Per-event imported details are capped at 2 MiB. Migration and restore scope, catalog aliases, stale writes, deletion snapshots and transaction rollback are covered by test_unified.py and test_clinics.py. Physical Android/Windows acceptance remains required.
