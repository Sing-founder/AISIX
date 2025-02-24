from flask import Flask, render_template, request, redirect, send_file
import sqlite3
from datetime import datetime
import csv
import os
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)

# Set up AISIX database
def init_db():
    conn = sqlite3.connect('aisix_patients.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS patients 
                 (id TEXT, admit_time TEXT, symptoms TEXT, diagnosis TEXT, 
                  vitals TEXT, hospital TEXT, sync TEXT, notes TEXT)''')
    conn.commit()
    conn.close()

# Simple AI risk prediction
def predict_risk(symptoms):
    symptoms = symptoms.lower()
    if "fever" in symptoms and "cough" in symptoms:
        return "High Flu Risk"
    elif "fever" in symptoms:
        return "Moderate Infection Risk"
    elif "cough" in symptoms or "shortness of breath" in symptoms:
        return "Possible Respiratory Issue"
    else:
        return "Low Risk"

# Generate pie chart for disease prevalence
def plot_disease_pie(prevalence):
    labels = [diag for diag, _, _ in prevalence]
    sizes = [count for _, count, _ in prevalence]
    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    return img_str

# Generate bar chart for symptom prevalence
def plot_symptom_bar(symptom_stats):
    symptoms = [symptom for symptom, _, _ in symptom_stats]
    counts = [count for _, count, _ in symptom_stats]
    fig, ax = plt.subplots()
    ax.bar(symptoms, counts, color=['#ff9999', '#66b3ff'])
    ax.set_ylabel('Number of Cases')
    ax.set_title('Symptom Prevalence')
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    return img_str

# Generate line chart for admissions over time
def plot_admissions_over_time(patients):
    dates = [datetime.strptime(p[1], '%Y-%m-%d %H:%M').date() for p in patients]
    date_counts = {}
    for date in dates:
        date_counts[date] = date_counts.get(date, 0) + 1
    fig, ax = plt.subplots()
    ax.plot(list(date_counts.keys()), list(date_counts.values()), marker='o')
    ax.set_xlabel('Date')
    ax.set_ylabel('Admissions')
    ax.set_title('Admissions Over Time')
    plt.xticks(rotation=45)
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    return img_str

# Home page - patient list
@app.route('/')
def index():
    conn = sqlite3.connect('aisix_patients.db')
    c = conn.cursor()
    c.execute("SELECT * FROM patients")
    patients = [(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], predict_risk(row[2])) for row in c.fetchall()]
    conn.close()
    return render_template('index.html', patients=patients)

# Add patient
@app.route('/add', methods=['POST'])
def add_patient():
    id = request.form['id']
    admit_time = datetime.now().strftime('%Y-%m-%d %H:%M')
    symptoms = request.form['symptoms']
    diagnosis = request.form['diagnosis']
    vitals = request.form['vitals']
    hospital = request.form['hospital']
    sync = request.form['sync']
    notes = request.form['notes']
    
    conn = sqlite3.connect('aisix_patients.db')
    c = conn.cursor()
    c.execute("INSERT INTO patients VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
              (id, admit_time, symptoms, diagnosis, vitals, hospital, sync, notes))
    conn.commit()
    conn.close()
    return redirect('/')

# AISIX Dashboard with charts
@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect('aisix_patients.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM patients")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM patients WHERE symptoms LIKE '%Fever%'")
    fever_cases = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM patients WHERE symptoms LIKE '%Cough%'")
    cough_cases = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT hospital) FROM patients WHERE sync='Y'")
    synced_hospitals = c.fetchone()[0]
    alert = "Check: Fever Spike" if fever_cases > 3 else "No Alert"
    
    # Prevalence by diagnosis
    c.execute("SELECT diagnosis, COUNT(*) as count FROM patients GROUP BY diagnosis")
    prevalence_data = c.fetchall()
    prevalence = [(diag, count, round((count/total)*100, 2) if total > 0 else 0) 
                  for diag, count in prevalence_data if diag]
    
    # Symptom prevalence
    symptom_stats = [
        ("Fever", fever_cases, round((fever_cases/total)*100, 2) if total > 0 else 0),
        ("Cough", cough_cases, round((cough_cases/total)*100, 2) if total > 0 else 0)
    ]
    
    # Get all patients for admissions chart
    c.execute("SELECT * FROM patients")
    patients = c.fetchall()
    conn.close()
    
    # Generate charts
    disease_pie = plot_disease_pie(prevalence)
    symptom_bar = plot_symptom_bar(symptom_stats)
    admissions_line = plot_admissions_over_time(patients)
    
    return render_template('dashboard.html', total=total, fever_cases=fever_cases,
                          synced_hospitals=synced_hospitals, alert=alert, 
                          prevalence=prevalence, symptom_stats=symptom_stats,
                          disease_pie=disease_pie, symptom_bar=symptom_bar,
                          admissions_line=admissions_line)

# Export data for research
@app.route('/export')
def export_data():
    conn = sqlite3.connect('aisix_patients.db')
    c = conn.cursor()
    c.execute("SELECT * FROM patients")
    patients = c.fetchall()
    conn.close()
    
    csv_path = 'aisix_research_data.csv'
    with open(csv_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['ID', 'Admit Time', 'Symptoms', 'Diagnosis', 'Vitals', 
                        'Hospital', 'Sync?', 'Notes'])
        writer.writerows(patients)
    
    return send_file(csv_path, as_attachment=True)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)