# PART 1: Data Management

import sqlite3
import csv
import pandas as pd

print("PART 1: Data Management")

conn = sqlite3.connect("ImmuneDrugTrial.db")
cur = conn.cursor()

cur.execute("PRAGMA foreign_keys = ON;")

cur.executescript("""
DROP TABLE IF EXISTS countCSVStaging;
DROP TABLE IF EXISTS Samples;
DROP TABLE IF EXISTS Subjects;

CREATE TABLE countCSVStaging (
    project TEXT,
    subject TEXT,
    condition TEXT,
    age INTEGER,
    sex TEXT,
    treatment TEXT,
    response TEXT,
    sample TEXT,
    sample_type TEXT,
    time_from_treatment INTEGER,
    b_cell INTEGER,
    cd8_t_cell INTEGER,
    cd4_t_cell INTEGER,
    nk_cell INTEGER,
    monocyte INTEGER
);

CREATE TABLE Subjects (
    project TEXT,
    subject TEXT PRIMARY KEY,
    condition TEXT,
    age INTEGER,
    sex TEXT,
    treatment TEXT,
    response TEXT
);

CREATE TABLE Samples (
    subject TEXT,
    sample TEXT PRIMARY KEY,
    sample_type TEXT,
    time_from_treatment INTEGER,
    b_cell INTEGER,
    cd8_t_cell INTEGER,
    cd4_t_cell INTEGER,
    nk_cell INTEGER,
    monocyte INTEGER,
    FOREIGN KEY (subject) REFERENCES Subjects(subject)
);
""")

with open("cell-count.csv", newline="") as f:
    reader = csv.reader(f)
    next(reader)
    cur.executemany("""
        INSERT INTO countCSVStaging VALUES (
            ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
        )
    """, reader)

cur.executescript("""
INSERT INTO Subjects
SELECT DISTINCT
    project, subject, condition, age, sex, treatment, response
FROM countCSVStaging;

INSERT INTO Samples
SELECT DISTINCT
    subject, sample, sample_type, time_from_treatment,
    b_cell, cd8_t_cell, cd4_t_cell, nk_cell, monocyte
FROM countCSVStaging;

DROP TABLE countCSVStaging;
""")

conn.commit()
conn.close()

# Part 2: Initial Analysis - Data Overview

print("Part 2: Initial Analysis - Data Overview")

conn = sqlite3.connect("ImmuneDrugTrial.db")
cur = conn.cursor()

cur.executescript("""
CREATE VIEW IF NOT EXISTS SampleCellFrequencies AS
WITH totals AS (
    SELECT
        subject,
        sample,
        (b_cell + cd8_t_cell + cd4_t_cell + nk_cell + monocyte) AS total_count,
        b_cell,
        cd8_t_cell,
        cd4_t_cell,
        nk_cell,
        monocyte
    FROM Samples
)
SELECT
    subject,
    sample,
    total_count,
    'b_cell' AS population,
    b_cell AS count,
    100.0 * b_cell / total_count AS percentage
FROM totals

UNION ALL

SELECT
    subject,
    sample,
    total_count,
    'cd8_t_cell',
    cd8_t_cell,
    100.0 * cd8_t_cell / total_count
FROM totals

UNION ALL

SELECT
    subject,
    sample,
    total_count,
    'cd4_t_cell',
    cd4_t_cell,
    100.0 * cd4_t_cell / total_count
FROM totals

UNION ALL

SELECT
    subject,
    sample,
    total_count,
    'nk_cell',
    nk_cell,
    100.0 * nk_cell / total_count
FROM totals

UNION ALL

SELECT
    subject,
    sample,
    total_count,
    'monocyte',
    monocyte,
    100.0 * monocyte / total_count
FROM totals;

""")

df = pd.read_sql("""
SELECT *
FROM SampleCellFrequencies
ORDER BY sample, population;
""", conn)

print(df.head())

conn.commit()
conn.close()

# Part 3: Statistical Analysis
print("Part 3: Statistical Analysis")

import seaborn as sns
import matplotlib.pyplot as plt
from scipy import stats

conn = sqlite3.connect("ImmuneDrugTrial.db")
cur = conn.cursor()

bCellDf = pd.read_sql("""
SELECT Subjects.response, SampleCellFrequencies.percentage
FROM SampleCellFrequencies
JOIN Samples ON Samples.sample = SampleCellFrequencies.sample
JOIN Subjects ON Subjects.subject = Samples.subject
WHERE Subjects.treatment = 'miraclib'
  AND Subjects.condition = 'melanoma'
  AND Samples.sample_type = 'PBMC'
  AND SampleCellFrequencies.population = 'b_cell'
""", conn)

cd8CellDf = pd.read_sql("""
SELECT Subjects.response, SampleCellFrequencies.percentage
FROM SampleCellFrequencies
JOIN Samples ON Samples.sample = SampleCellFrequencies.sample
JOIN Subjects ON Subjects.subject = Samples.subject
WHERE Subjects.treatment = 'miraclib'
  AND Subjects.condition = 'melanoma'
  AND Samples.sample_type = 'PBMC'
  AND SampleCellFrequencies.population = 'cd8_t_cell'
""", conn)

cd4CellDf = pd.read_sql("""
SELECT Subjects.response, SampleCellFrequencies.percentage
FROM SampleCellFrequencies
JOIN Samples ON Samples.sample = SampleCellFrequencies.sample
JOIN Subjects ON Subjects.subject = Samples.subject
WHERE Subjects.treatment = 'miraclib'
  AND Subjects.condition = 'melanoma'
  AND Samples.sample_type = 'PBMC'
  AND SampleCellFrequencies.population = 'cd4_t_cell'
""", conn)

nkCellDf = pd.read_sql("""
SELECT Subjects.response, SampleCellFrequencies.percentage
FROM SampleCellFrequencies
JOIN Samples ON Samples.sample = SampleCellFrequencies.sample
JOIN Subjects ON Subjects.subject = Samples.subject
WHERE Subjects.treatment = 'miraclib'
  AND Subjects.condition = 'melanoma'
  AND Samples.sample_type = 'PBMC'
  AND SampleCellFrequencies.population = 'nk_cell'
""", conn)

monocyteCellDf = pd.read_sql("""
SELECT Subjects.response, SampleCellFrequencies.percentage
FROM SampleCellFrequencies
JOIN Samples ON Samples.sample = SampleCellFrequencies.sample
JOIN Subjects ON Subjects.subject = Samples.subject
WHERE Subjects.treatment = 'miraclib'
  AND Subjects.condition = 'melanoma'
  AND Samples.sample_type = 'PBMC'
  AND SampleCellFrequencies.population = 'monocyte'
""", conn)

dfs = [
    ("B Cell", bCellDf),
    ("CD8 T Cell", cd8CellDf),
    ("CD4 T Cell", cd4CellDf),
    ("NK Cell", nkCellDf),
    ("Monocyte", monocyteCellDf)
]

for name, df in dfs:
    plt.figure()
    sns.boxplot(x='response', y='percentage', data=df)

    plt.title(name + ' Relative Frequency by Drug Response')
    plt.xlabel('Patient Responded to Drug')
    plt.ylabel(name + ' Relative Frequency Percentage')
    plt.show()

for name, df in dfs:
    responders = df.loc[df['response'] == 'yes', "percentage"]
    nonresponders = df.loc[df['response'] == 'no', "percentage"]
    
    t_stat, p_value = stats.ttest_ind(responders, nonresponders, equal_var=True)
    
    print(f"{name}")
    print(f"  T-statistic: {t_stat:.3f}")
    print(f"  P-value: {p_value:.4f}\n")

conn.close()

print("We can reject the null hypothesis only for CD4 T Cells, which exhibited a p-value of 0.005 < alpha value of 0.05. The relative frequency of CD4 T Cells significantly differs between melanoma patients who respond versus those who do not respond to Miraclib treatment in PBMC samples. All other cell populations (B Cells, CD8 T Cells, NK Cells, Monocytes) showed no statistically significant differences between responders and non-responders.")

# Part 4: Data Subset Analysis
print("Part 4: Data Subset Analysis")

conn = sqlite3.connect("ImmuneDrugTrial.db")
cur = conn.cursor()

filter_condition = """
Subjects.treatment = 'miraclib' AND
Subjects.condition = 'melanoma' AND
Samples.sample_type = 'PBMC' AND
Samples.time_from_treatment = 0
"""
query1 = f"""
SELECT Samples.sample, Subjects.subject, Subjects.project, Subjects.response, Subjects.sex
FROM Samples
JOIN Subjects ON Subjects.subject = Samples.subject
WHERE {filter_condition}
ORDER BY Samples.sample
"""
baseline_samples = pd.read_sql(query1, conn)
print("Baseline PBMC melanoma samples:")
print(baseline_samples.head())

query2 = f"""
SELECT Subjects.project, COUNT(Samples.sample) AS num_samples
FROM Samples
JOIN Subjects ON Subjects.subject = Samples.subject
WHERE {filter_condition}
GROUP BY Subjects.project
"""
samples_per_project = pd.read_sql(query2, conn)
print("Samples per project:")
print(samples_per_project, "\n")

query3 = f"""
SELECT Subjects.response, COUNT(DISTINCT Subjects.subject) AS num_subjects
FROM Samples
JOIN Subjects ON Subjects.subject = Samples.subject
WHERE {filter_condition}
GROUP BY Subjects.response
"""
subjects_per_response = pd.read_sql(query3, conn)
print("Subjects per response (yes/no):")
print(subjects_per_response, "\n")

query4 = f"""
SELECT Subjects.sex, COUNT(DISTINCT Subjects.subject) AS num_subjects
FROM Samples
JOIN Subjects ON Subjects.subject = Samples.subject
WHERE {filter_condition}
GROUP BY Subjects.sex
"""
subjects_per_sex = pd.read_sql(query4, conn)
print("Subjects per sex (M/F):")
print(subjects_per_sex, "\n")

conn.close()

# Google Form Question
print("Google Form Question")

conn = sqlite3.connect("ImmuneDrugTrial.db")
cur = conn.cursor()

df = pd.read_sql(
    """        
    SELECT Subjects.project, Samples.b_cell
    FROM Samples
    JOIN Subjects ON Subjects.subject = Samples.subject
    WHERE Subjects.condition = "melanoma" AND Subjects.response = "yes" AND Subjects.sex = "M" AND Samples.time_from_treatment = 0
    """, conn)

print(round(df["b_cell"].mean(),2))

conn.close()

