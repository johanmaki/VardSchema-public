# database.py
import sqlite3
from datetime import datetime

DB_NAME = "vardschema.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS employees
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  hospital TEXT,
                  name TEXT,
                  workload INTEGER,
                  work_types TEXT,
                  max_consec_days INTEGER,
                  min_days_off INTEGER,
                  experience INTEGER,
                  last_updated DATETIME)''')
    conn.commit()
    conn.close()

def save_employee_prefs(data):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Kolla om redan finns
    c.execute('''SELECT * FROM employees 
                 WHERE hospital=? AND name=?''',
              (data["hospital"], data["name"]))
    exists = c.fetchone()
    
    if exists:
        c.execute('''UPDATE employees SET
                     workload=?, work_types=?, max_consec_days=?,
                     min_days_off=?, experience=?, last_updated=?
                     WHERE id=?''',
                  (data["workload"],
                   ",".join(data["work_types"]),
                   data["max_consecutive_days"],
                   data["min_days_off"],
                   data["experience"],
                   datetime.now(),
                   exists[0]))
    else:
        c.execute('''INSERT INTO employees 
                     (hospital, name, workload, work_types, 
                      max_consec_days, min_days_off, experience, last_updated)
                     VALUES (?,?,?,?,?,?,?,?)''',
                  (data["hospital"],
                   data["name"],
                   data["workload"],
                   ",".join(data["work_types"]),
                   data["max_consecutive_days"],
                   data["min_days_off"],
                   data["experience"],
                   datetime.now()))
    
    conn.commit()
    conn.close()

def get_employees(hospital):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''SELECT * FROM employees 
                 WHERE hospital=?''', (hospital,))
    employees = c.fetchall()
    conn.close()
    return employees

def update_employee(data):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''UPDATE employees SET
                 workload=?, work_types=?, max_consec_days=?,
                 min_days_off=?, experience=?, last_updated=?
                 WHERE id=?''',
              (data["workload"],
               ",".join(data["work_types"]),
               data["max_consecutive_days"],
               data["min_days_off"],
               data["experience"],
               datetime.now(),
               data["id"]))
    conn.commit()
    conn.close()

# Initiera databasen vid första import
init_db()
