-- ============================================================
-- db_setup.sql — MySQL setup for PlacementIQ student database
-- Run this once to create the tables used by mysql_placement_db tool
--
-- How to run:
--   mysql -u root -p < db_setup.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS placements_db;
USE placements_db;

-- ── Students table ────────────────────────────────────────────────────────
-- Stores college student records
CREATE TABLE IF NOT EXISTS students (
    id        INT AUTO_INCREMENT PRIMARY KEY,
    name      VARCHAR(100)  NOT NULL,
    roll_no   VARCHAR(20)   NOT NULL UNIQUE,   -- e.g. 21A91A0501
    branch    VARCHAR(50)   NOT NULL,           -- e.g. CSE, IT, ECE
    cgpa      DECIMAL(3,1)  NOT NULL,
    backlogs  INT           DEFAULT 0,
    year      INT           NOT NULL            -- graduation year
);

-- ── Companies table ───────────────────────────────────────────────────────
-- Eligibility criteria for each company that visits campus
CREATE TABLE IF NOT EXISTS companies (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    name              VARCHAR(100)  NOT NULL,
    min_cgpa          DECIMAL(3,1)  NOT NULL,
    allowed_branches  VARCHAR(200)  NOT NULL,   -- comma-separated, e.g. "CSE,IT,ECE"
    package_lpa       DECIMAL(5,2)  NOT NULL,
    bond_years        INT           DEFAULT 0
);

-- ── Placements table ──────────────────────────────────────────────────────
-- Records of students placed in companies
CREATE TABLE IF NOT EXISTS placements (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    student_id  INT           NOT NULL,
    company_id  INT           NOT NULL,
    year        INT           NOT NULL,
    package_lpa DECIMAL(5,2)  NOT NULL,
    status      VARCHAR(20)   DEFAULT 'placed',  -- placed / rejected / pending
    FOREIGN KEY (student_id) REFERENCES students(id),
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- ── Sample company data (matches PDF dataset) ─────────────────────────────
INSERT INTO companies (name, min_cgpa, allowed_branches, package_lpa, bond_years) VALUES
('TCS',          7.0, 'CSE,IT,ECE,EEE,MECH',  7.00, 1),
('Infosys',      6.5, 'CSE,IT,ECE,EEE,MECH',  6.50, 0),
('Wipro',        6.0, 'CSE,IT,ECE,EEE',        6.50, 0),
('Accenture',    6.5, 'CSE,IT,ECE,EEE,MECH',   9.00, 0),
('Cognizant',    6.5, 'CSE,IT,ECE',             8.00, 0),
('Capgemini',    6.0, 'CSE,IT,ECE,EEE,MECH',   7.00, 0),
('HCL',          6.5, 'CSE,IT,ECE',             9.00, 1),
('Tech Mahindra',6.5, 'CSE,IT,ECE',             7.50, 0),
('IBM',          7.0, 'CSE,IT,ECE',            10.00, 0),
('Deloitte',     7.0, 'CSE,IT,ECE',            11.00, 0),
('Amazon',       8.0, 'CSE,IT',                45.00, 0),
('Google',       8.5, 'CSE,IT',                50.00, 0),
('Microsoft',    8.0, 'CSE,IT',                45.00, 0),
('Adobe',        8.0, 'CSE,IT',                30.00, 0),
('Oracle',       7.5, 'CSE,IT',                18.00, 0),
('SAP',          7.5, 'CSE,IT,ECE',            18.00, 0),
('Qualcomm',     8.5, 'ECE,EEE',               42.00, 0),
('Intel',        8.0, 'ECE,EEE,CSE',           35.00, 0),
('Flipkart',     8.0, 'CSE,IT',                40.00, 0),
('Samsung R&D',  8.0, 'CSE,IT,ECE,EEE',        39.00, 0);

-- ── Sample student data ───────────────────────────────────────────────────
-- Add your real students here or import from your existing records
INSERT INTO students (name, roll_no, branch, cgpa, backlogs, year) VALUES
('Madhavi Reddy',    '21A91A0501', 'IT',  8.2, 0, 2025),
('Rahul Kumar',      '21A91A0502', 'CSE', 7.5, 0, 2025),
('Priya Sharma',     '21A91A0503', 'ECE', 7.8, 1, 2025),
('Sai Teja',         '21A91A0504', 'IT',  6.8, 0, 2025),
('Ananya Singh',     '21A91A0505', 'CSE', 9.1, 0, 2025),
('Vikram Naidu',     '21A91A0506', 'EEE', 7.2, 2, 2025),
('Lakshmi Prasad',   '21A91A0507', 'IT',  8.5, 0, 2025),
('Arjun Varma',      '21A91A0508', 'CSE', 6.2, 0, 2025),
('Deepika Rao',      '21A91A0509', 'ECE', 8.9, 0, 2025),
('Kiran Chandra',    '21A91A0510', 'MECH',7.0, 0, 2025);

-- ── Sample placement records ──────────────────────────────────────────────
INSERT INTO placements (student_id, company_id, year, package_lpa, status) VALUES
(1,  1,  2025, 7.00,  'placed'),   -- Madhavi → TCS
(2,  3,  2025, 6.50,  'placed'),   -- Rahul → Wipro
(5,  12, 2025, 50.00, 'placed'),   -- Ananya → Google
(7,  4,  2025, 9.00,  'placed'),   -- Lakshmi → Accenture
(9,  11, 2025, 45.00, 'placed'),   -- Deepika → Amazon
(3,  5,  2025, 8.00,  'placed'),   -- Priya → Cognizant
(4,  6,  2025, 7.00,  'placed'),   -- Sai Teja → Capgemini
(8,  1,  2025, 7.00,  'placed'),   -- Arjun → TCS
(10, 1,  2025, 7.00,  'placed'),   -- Kiran → TCS
(6,  7,  2025, 9.00,  'placed');   -- Vikram → HCL

-- ── Verify setup ──────────────────────────────────────────────────────────
SELECT 'Setup complete!' AS status;
SELECT COUNT(*) AS total_companies FROM companies;
SELECT COUNT(*) AS total_students  FROM students;
SELECT COUNT(*) AS total_placed    FROM placements WHERE status = 'placed';