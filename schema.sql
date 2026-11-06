PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
INSERT OR IGNORE INTO meta(key,value) VALUES('revision','0');
CREATE TABLE IF NOT EXISTS catalogs(kind TEXT NOT NULL,id TEXT NOT NULL,name TEXT NOT NULL,active INTEGER NOT NULL CHECK(active IN(0,1)),sort_order INTEGER NOT NULL,fee_bps INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(kind,id));
CREATE TABLE IF NOT EXISTS patients(id TEXT PRIMARY KEY,created INTEGER NOT NULL,first_name TEXT NOT NULL,last_name TEXT NOT NULL,mobile TEXT NOT NULL,legacy_name TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_patient_mobile ON patients(mobile);
CREATE INDEX IF NOT EXISTS idx_patient_name ON patients(first_name,last_name);
CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY,created INTEGER NOT NULL,service_date TEXT NOT NULL,patient TEXT NOT NULL,service TEXT NOT NULL,product TEXT NOT NULL,area TEXT NOT NULL,volume REAL NOT NULL CHECK(volume>0),unit TEXT NOT NULL,price INTEGER NOT NULL CHECK(price>=0),amount INTEGER NOT NULL CHECK(amount>=0),note TEXT NOT NULL,cost_reviewed INTEGER NOT NULL DEFAULT 0,divisor_milli INTEGER NOT NULL DEFAULT 2000,patient_id TEXT REFERENCES patients(id),details_json TEXT NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS payments(record_id TEXT NOT NULL REFERENCES records(id) ON DELETE CASCADE,id TEXT NOT NULL,amount INTEGER NOT NULL CHECK(amount>0),payment_date TEXT,method TEXT NOT NULL,method_label TEXT NOT NULL,stage TEXT NOT NULL,note TEXT NOT NULL,legacy INTEGER NOT NULL CHECK(legacy IN(0,1)),sort_order INTEGER NOT NULL,fee_bps INTEGER,PRIMARY KEY(record_id,id));
CREATE INDEX IF NOT EXISTS idx_service_date ON records(service_date);
CREATE INDEX IF NOT EXISTS idx_payment_date ON payments(payment_date);

CREATE TABLE IF NOT EXISTS receipts(id TEXT PRIMARY KEY,created INTEGER NOT NULL,receipt_date TEXT NOT NULL,product_id TEXT NOT NULL,product_label TEXT NOT NULL,quantity_milli INTEGER NOT NULL CHECK(quantity_milli>0),pack_unit TEXT NOT NULL,contents_milli INTEGER NOT NULL CHECK(contents_milli>0),base_unit TEXT NOT NULL,unit_price INTEGER NOT NULL CHECK(unit_price>=0),received_milli INTEGER NOT NULL CHECK(received_milli>0),total_cost INTEGER NOT NULL CHECK(total_cost>=0),note TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS consumptions(record_id TEXT NOT NULL REFERENCES records(id) ON DELETE CASCADE,id TEXT NOT NULL,receipt_id TEXT NOT NULL REFERENCES receipts(id),quantity_milli INTEGER NOT NULL CHECK(quantity_milli>0),sort_order INTEGER NOT NULL,PRIMARY KEY(record_id,id));
CREATE INDEX IF NOT EXISTS idx_receipt_date ON receipts(receipt_date);

CREATE TABLE IF NOT EXISTS activity_log(id INTEGER PRIMARY KEY AUTOINCREMENT,occurred_at TEXT NOT NULL,local_day TEXT NOT NULL,action TEXT NOT NULL,entity_type TEXT NOT NULL,entity_id TEXT NOT NULL,label TEXT NOT NULL,details_json TEXT NOT NULL,imported INTEGER NOT NULL DEFAULT 0,source_key TEXT UNIQUE);
CREATE INDEX IF NOT EXISTS idx_log_day ON activity_log(local_day,id);
CREATE INDEX IF NOT EXISTS idx_log_action ON activity_log(action,entity_type,id);
CREATE TABLE IF NOT EXISTS app_releases(version_code INTEGER PRIMARY KEY,version_name TEXT NOT NULL,release_date TEXT NOT NULL,changes_json TEXT NOT NULL);
