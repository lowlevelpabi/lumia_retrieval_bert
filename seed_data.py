"""
seed_data.py — Direct DB + Qdrant seeder for dummy thesis and capstone papers.
Run: python seed_data.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal, init_db
from app.models.paper import Paper
from app.services.embedding_service import embedding_service
from app.services.vector_db import vector_db

PAPERS = [
    {
        "title": "Deep Learning-Based Intrusion Detection System for IoT Networks in Smart Home Environments",
        "author": "Juan Miguel Santos, Maria Angelica Reyes, Paolo Emmanuel Cruz",
        "year": "2023",
        "abstract": (
            "The proliferation of Internet of Things (IoT) devices in smart home environments has introduced "
            "significant cybersecurity challenges. Traditional rule-based intrusion detection systems (IDS) "
            "often fail to adapt to the evolving threat landscape. This study proposes a deep learning-based "
            "IDS leveraging Long Short-Term Memory (LSTM) networks to detect anomalous network traffic in "
            "real-time. The system was trained on the CICIDS2017 dataset augmented with synthetic IoT traffic. "
            "Results demonstrate a detection accuracy of 97.4% with a false-positive rate of 1.2%, "
            "outperforming conventional machine learning approaches including Random Forest and SVM."
        ),
        "department": "Computer Science",
        "keywords": "deep learning, LSTM, intrusion detection, IoT, cybersecurity, smart home",
        "project_type": "Thesis",
        "degree_program": "BSCS",
        "citation_count": 5,
        "view_count": 42,
        "file_path": "uploads/dummy_iot_ids_thesis.pdf",
    },
    {
        "title": "Predicting Student Academic Performance Using Ensemble Machine Learning in a Philippine University Setting",
        "author": "Leilani Delos Santos, Kristoffer James Villanueva",
        "year": "2022",
        "abstract": (
            "Early identification of at-risk students is a critical concern for academic institutions. "
            "This thesis presents an ensemble machine learning framework combining Gradient Boosting, "
            "Random Forest, and k-Nearest Neighbors to predict final academic grades based on behavioral, "
            "social, and academic attributes. Data was collected from 1,200 undergraduate students over "
            "three academic years. The proposed ensemble achieves an accuracy of 89.7% (F1: 0.88), "
            "surpassing standalone classifiers. A web-based dashboard was developed for faculty use, "
            "enabling proactive intervention mechanisms aligned with the university's academic support programs."
        ),
        "department": "Information Systems",
        "keywords": "machine learning, ensemble methods, academic performance, student prediction, education analytics",
        "project_type": "Thesis",
        "degree_program": "BSIS",
        "citation_count": 12,
        "view_count": 88,
        "file_path": "uploads/dummy_student_performance_thesis.pdf",
    },
    {
        "title": "LinguaCheck: An Automated Grammar and Style Checker for Filipino-English Academic Writing Using NLP",
        "author": "Alicia Fernandez, Ronaldo Macaraeg, Stephanie Anne Tan, Jerome Aquino",
        "year": "2024",
        "abstract": (
            "Code-switching in academic writing poses unique challenges for automated grammar checking tools "
            "trained predominantly on monolingual corpora. LinguaCheck is a capstone system designed to address "
            "grammatical and stylistic errors in Filipino-English mixed academic documents. Built on a fine-tuned "
            "BERT model trained on 15,000 locally-sourced academic paragraphs, the system identifies ten error "
            "categories including subject-verb agreement, article misuse, and Taglish sentence fragments. "
            "User testing with 60 undergraduate volunteers yielded a System Usability Scale (SUS) score of 83.4, "
            "indicating excellent usability and practical value for local academic writing contexts."
        ),
        "department": "Information Technology",
        "keywords": "NLP, BERT, grammar checking, code-switching, Filipino-English, academic writing",
        "project_type": "Capstone Project",
        "degree_program": "BSIT",
        "citation_count": 3,
        "view_count": 27,
        "file_path": "uploads/dummy_linguacheck_capstone.pdf",
    },
    {
        "title": "SmartBridge: An IoT-Based Structural Health Monitoring System for Pedestrian Bridges",
        "author": "Rafael Antonio Navarro, Jessa Marie Ocampo, Dennis Alcantara",
        "year": "2023",
        "abstract": (
            "Aging pedestrian infrastructure in urban areas represents a persistent public safety concern. "
            "SmartBridge is a low-cost, IoT-enabled structural health monitoring (SHM) system designed for "
            "real-time detection of stress, vibration, and displacement anomalies in pedestrian bridges. "
            "The system integrates accelerometers, strain gauges, and a Raspberry Pi 4-based edge computing "
            "node to transmit sensor data to a cloud dashboard via MQTT. A threshold-based alert system "
            "notifies local engineers of abnormal readings. Field deployment on a 45-meter footbridge over "
            "60 days confirmed system reliability with 99.1% uptime and sub-3-second alert latency."
        ),
        "department": "Computer Engineering",
        "keywords": "IoT, structural health monitoring, Raspberry Pi, MQTT, edge computing, bridge safety",
        "project_type": "Capstone Project",
        "degree_program": "BSCpE",
        "citation_count": 7,
        "view_count": 61,
        "file_path": "uploads/dummy_smartbridge_capstone.pdf",
    },
]

def seed():
    print("Initializing database tables...")
    init_db()
    db = SessionLocal()
    try:
        for data in PAPERS:
            paper = db.query(Paper).filter(Paper.title == data["title"]).first()
            
            if paper:
                print(f"[UPDATE] Updating: {data['title'][:60]}...")
                for key, value in data.items():
                    setattr(paper, key, value)
            else:
                paper = Paper(**data)
                db.add(paper)
                print(f"[INSERT] New: {data['title'][:60]}...")
            
            db.flush()  # Get the ID

            # Sync to Qdrant
            try:
                title_vec = embedding_service.get_embedding(paper.title)
                abstract_vec = embedding_service.get_embedding(paper.abstract)
                vector_db.upsert_paper(
                    paper_id=paper.id,
                    vectors={"title": title_vec, "abstract": abstract_vec},
                    metadata={
                        "title": paper.title,
                        "author": paper.author,
                        "year": paper.year,
                        "abstract": paper.abstract,
                        "department": paper.department,
                        "keywords": paper.keywords,
                        "project_type": paper.project_type,
                        "degree_program": paper.degree_program,
                        "citation_count": paper.citation_count,
                        "view_count": paper.view_count,
                    }
                )
                print(f"[QDRANT] Synced: ID {paper.id}")
            except Exception as e:
                print(f"[QDRANT ERROR] Could not sync ID {paper.id}: {e}")

        db.commit()
        print(f"\n✅ Seeded {len(PAPERS)} papers successfully.")
    except Exception as e:
        db.rollback()
        print(f"❌ Error during seeding: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed()
