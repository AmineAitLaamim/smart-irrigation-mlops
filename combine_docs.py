import os

# Define organized order with categories
docs_order = [
    # Section 1: Getting Started
    ("SETUP_GUIDE.md", "Getting Started Guide"),
    ("PROJECT_TREE.md", "Project Structure & File Tree"),
    
    # Section 2: Architecture
    ("ARCHITECTURE.md", "System Architecture"),
    ("SYSTEM_SCHEMA.md", "Complete System Schema"),
    ("MICROSERVICES.md", "Microservices Overview"),
    ("END_TO_END_DATA_FLOW.md", "End-to-End Data Flow"),
    
    # Section 3: Infrastructure
    ("INFRASTRUCTURE.md", "Infrastructure & Docker Compose"),
    ("NGINX.md", "Nginx Reverse Proxy"),
    ("DATABASE.md", "Database Schema"),
    ("DATABASE_SCHEMA.md", "Database Schema Details"),
    
    # Section 4: Services - Core
    ("API_GATEWAY.md", "API Gateway"),
    ("USER_SERVICE.md", "User Service & Authentication"),
    
    # Section 5: Services - Data Pipeline
    ("SENSOR_SIMULATOR.md", "Sensor Simulator"),
    ("DATA_INGESTION.md", "Data Ingestion Service"),
    ("FEATURE_ENGINEERING.md", "Feature Engineering"),
    ("FEATURE_ENGINEERING_GUIDE.md", "Feature Engineering Guide"),
    ("DATA_QUALITY.md", "Data Quality Service"),
    
    # Section 6: Services - ML
    ("MODEL_SERVER.md", "Model Server"),
    ("MODEL_SERVER_API.md", "Model Server API"),
    ("MODEL_VERSIONING.md", "Model Versioning"),
    ("DRIFT_MONITORING.md", "Drift Monitoring"),
    ("IRRIGATION_SYSTEM.md", "Irrigation Trigger System"),
    
    # Section 7: ML Pipeline & Training
    ("ML_PIPELINE.md", "ML Pipeline"),
    ("ML_TRAINING_GUIDE.md", "ML Training Guide"),
    ("ML_EXPLORATION.md", "ML Exploration"),
    ("ML_DEMO_SCRIPT.md", "ML Demo Script"),
    ("model_cards/soil_moisture_model_template.md", "Model Card Template"),
    
    # Section 8: CI/CD & DevOps
    ("JENKINS.md", "Jenkins CI/CD"),
    ("AIRFLOW.md", "Airflow DAG Pipeline"),
    
    # Section 9: Frontend
    ("WEB_DASHBOARD.md", "Web Dashboard"),
    
    # Section 10: Monitoring & Alerts
    ("PROMETHEUS.md", "Prometheus Monitoring"),
    ("GRAFANA.md", "Grafana Dashboards"),
    ("ALERTMANAGER.md", "Alertmanager"),
    ("NOTIFICATION_SERVICE.md", "Notification Service"),
    
    # Section 11: Deployment & Operations
    ("DEPLOYMENT.md", "Deployment Guide"),
    ("TESTING.md", "Testing Guide"),
    
    # Section 12: Development Practices
    ("CODE_REVIEW.md", "Code Review Guidelines"),
    ("BRANCH_NAMING.md", "Branch Naming Convention"),
]

docs_dir = "docs"
output_file = "smart-irrigation-docs.md"

# Section headers
section_headers = {
    "Getting Started Guide": "═══════════════════════════════════════════════════════════════════",
    "Project Structure & File Tree": "═══════════════════════════════════════════════════════════════════",
    "System Architecture": "═══════════════════════════════════════════════════════════════════",
    "Complete System Schema": "═══════════════════════════════════════════════════════════════════",
    "Microservices Overview": "═══════════════════════════════════════════════════════════════════",
    "End-to-End Data Flow": "═══════════════════════════════════════════════════════════════════",
    "Infrastructure & Docker Compose": "═══════════════════════════════════════════════════════════════════",
    "Nginx Reverse Proxy": "═══════════════════════════════════════════════════════════════════",
    "Database Schema": "═══════════════════════════════════════════════════════════════════",
    "Database Schema Details": "═══════════════════════════════════════════════════════════════════",
    "API Gateway": "═══════════════════════════════════════════════════════════════════",
    "User Service & Authentication": "═══════════════════════════════════════════════════════════════════",
    "Sensor Simulator": "═══════════════════════════════════════════════════════════════════",
    "Data Ingestion Service": "═══════════════════════════════════════════════════════════════════",
    "Feature Engineering": "═══════════════════════════════════════════════════════════════════",
    "Feature Engineering Guide": "═══════════════════════════════════════════════════════════════════",
    "Data Quality Service": "═══════════════════════════════════════════════════════════════════",
    "Model Server": "═══════════════════════════════════════════════════════════════════",
    "Model Server API": "═══════════════════════════════════════════════════════════════════",
    "Model Versioning": "═══════════════════════════════════════════════════════════════════",
    "Drift Monitoring": "═══════════════════════════════════════════════════════════════════",
    "Irrigation Trigger System": "═══════════════════════════════════════════════════════════════════",
    "ML Pipeline": "═══════════════════════════════════════════════════════════════════",
    "ML Training Guide": "═══════════════════════════════════════════════════════════════════",
    "ML Exploration": "═══════════════════════════════════════════════════════════════════",
    "ML Demo Script": "═══════════════════════════════════════════════════════════════════",
    "Model Card Template": "═══════════════════════════════════════════════════════════════════",
    "Jenkins CI/CD": "═══════════════════════════════════════════════════════════════════",
    "Airflow DAG Pipeline": "═══════════════════════════════════════════════════════════════════",
    "Web Dashboard": "═══════════════════════════════════════════════════════════════════",
    "Prometheus Monitoring": "═══════════════════════════════════════════════════════════════════",
    "Grafana Dashboards": "═══════════════════════════════════════════════════════════════════",
    "Alertmanager": "═══════════════════════════════════════════════════════════════════",
    "Notification Service": "═══════════════════════════════════════════════════════════════════",
    "Deployment Guide": "═══════════════════════════════════════════════════════════════════",
    "Testing Guide": "═══════════════════════════════════════════════════════════════════",
    "Code Review Guidelines": "═══════════════════════════════════════════════════════════════════",
    "Branch Naming Convention": "═══════════════════════════════════════════════════════════════════",
}

print("=" * 80)
print("SMART IRRIGATION SYSTEM - COMPLETE DOCUMENTATION")
print("=" * 80)

with open(output_file, "w", encoding="utf-8") as out:
    out.write("╔══════════════════════════════════════════════════════════════════════════════╗\n")
    out.write("║                   SMART IRRIGATION SYSTEM - COMPLETE DOCUMENTATION            ║\n")
    out.write("╚══════════════════════════════════════════════════════════════════════════════╝\n\n")
    out.write("This document contains the complete documentation for the Smart Irrigation System.\n")
    out.write("Organized into 12 sections covering architecture, services, ML, DevOps, and operations.\n\n")
    
    out.write("─" * 80 + "\n")
    out.write("TABLE OF CONTENTS\n")
    out.write("─" * 80 + "\n\n")
    
    # Generate table of contents
    sections = {}
    for filename, title in docs_order:
        if title in ["Getting Started Guide", "Project Structure & File Tree"]:
            section = "1. GETTING STARTED"
        elif title in ["System Architecture", "Complete System Schema", "Microservices Overview", "End-to-End Data Flow"]:
            section = "2. ARCHITECTURE"
        elif title in ["Infrastructure & Docker Compose", "Nginx Reverse Proxy", "Database Schema", "Database Schema Details"]:
            section = "3. INFRASTRUCTURE"
        elif title in ["API Gateway", "User Service & Authentication"]:
            section = "4. CORE SERVICES"
        elif title in ["Sensor Simulator", "Data Ingestion Service", "Feature Engineering", "Feature Engineering Guide", "Data Quality Service"]:
            section = "5. DATA PIPELINE SERVICES"
        elif title in ["Model Server", "Model Server API", "Model Versioning", "Drift Monitoring", "Irrigation Trigger System"]:
            section = "6. ML SERVICES"
        elif title in ["ML Pipeline", "ML Training Guide", "ML Exploration", "ML Demo Script", "Model Card Template"]:
            section = "7. ML PIPELINE & TRAINING"
        elif title in ["Jenkins CI/CD", "Airflow DAG Pipeline"]:
            section = "8. CI/CD & DEVOPS"
        elif title in ["Web Dashboard"]:
            section = "9. FRONTEND"
        elif title in ["Prometheus Monitoring", "Grafana Dashboards", "Alertmanager", "Notification Service"]:
            section = "10. MONITORING & ALERTS"
        elif title in ["Deployment Guide", "Testing Guide"]:
            section = "11. DEPLOYMENT & OPERATIONS"
        else:
            section = "12. DEVELOPMENT PRACTICES"
        
        if section not in sections:
            sections[section] = []
        sections[section].append(title)
    
    for section, titles in sections.items():
        out.write(f"\n{section}\n")
        for t in titles:
            out.write(f"  • {t}\n")
    
    out.write("\n")
    out.write("─" * 80 + "\n")
    out.write("DOCUMENT CONTENT\n")
    out.write("─" * 80 + "\n\n")
    
    for filename, title in docs_order:
        filepath = os.path.join(docs_dir, filename)
        if os.path.exists(filepath):
            print(f"Processing: {filename}")
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            header = section_headers.get(title, "=" * 80)
            
            out.write("\n" + header + "\n\n")
            out.write(f"SECTION: {title}\n\n")
            out.write(content + "\n\n")
        else:
            print(f"Skipping (not found): {filename}")

print(f"\nDone! Created: {output_file}")
print(f"Total sections: {len(docs_order)}")