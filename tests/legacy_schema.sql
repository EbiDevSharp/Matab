PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
INSERT OR IGNORE INTO meta(key,value) VALUES('revision','0');
CREATE TABLE IF NOT EXISTS catalogs(kind TEXT NOT NULL,id TEXT NOT NULL,name TEXT NOT NULL,active INTEGER NOT NULL CHECK(active IN(0,1)),sort_order INTEGER NOT NULL,PRIMARY KEY(kind,id));
CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY,created INTEGER NOT NULL,service_date TEXT NOT NULL,patient TEXT NOT NULL,service TEXT NOT NULL,product TEXT NOT NULL,area TEXT NOT NULL,volume REAL NOT NULL CHECK(volume>0),unit TEXT NOT NULL,price INTEGER NOT NULL CHECK(price>=0),amount INTEGER NOT NULL CHECK(amount>=0),note TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS payments(record_id TEXT NOT NULL REFERENCES records(id) ON DELETE CASCADE,id TEXT NOT NULL,amount INTEGER NOT NULL CHECK(amount>0),payment_date TEXT,method TEXT NOT NULL,method_label TEXT NOT NULL,stage TEXT NOT NULL,note TEXT NOT NULL,legacy INTEGER NOT NULL CHECK(legacy IN(0,1)),sort_order INTEGER NOT NULL,PRIMARY KEY(record_id,id));
CREATE INDEX IF NOT EXISTS idx_service_date ON records(service_date);
CREATE INDEX IF NOT EXISTS idx_payment_date ON payments(payment_date);
