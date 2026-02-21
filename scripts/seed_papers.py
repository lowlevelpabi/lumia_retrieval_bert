import sys
import os
import shutil
from datetime import datetime

# Add the parent directory to sys.path to allow importing from 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, engine
from app.models.paper import Paper, Base
from app.services.vector_db import vector_db
from app.services.embedding_service import embedding_service
from sqlalchemy import text

# --- DUMMY DATASET ---
DUMMY_PAPERS = [
    # Computer Science - AI/ML
    {
        "title": "Advances in Generative Adversarial Networks for Image Synthesis",
        "author": "Dr. Alan Turing, Maria Garcia",
        "year": "2024",
        "department": "Computer Science",
        "abstract": "This study explores novel architectures in Generative Adversarial Networks (GANs) to improve the stability and resolution of synthesized images. We introduce a multi-level discriminator approach that significantly reduces mode collapse in high-dimensional data distributions.",
        "keywords": "GAN, Deep Learning, Image Synthesis, Artificial Intelligence",
        "citation_count": 45
    },
    {
        "title": "Optimizing Transformer Models for Edge Computing Devices",
        "author": "Lei Zhang, Robert Smith",
        "year": "2023",
        "department": "Computer Science",
        "abstract": "Transformer models have revolutionized NLP but remain computationally expensive. This research proposes a pruning and quantization framework that allows BERT-based models to run efficiently on mobile hardware without sacrificing significant accuracy.",
        "keywords": "Edge Computing, Transformer, BERT, Model Compression",
        "citation_count": 12
    },
    {
        "title": "Explainable AI in Medical Diagnosis: A Comparative Analysis",
        "author": "Sarah Jenkins",
        "year": "2024",
        "department": "Computer Science",
        "abstract": "As deep learning models are increasingly used in healthcare, explainability becomes critical. We evaluate LIME and SHAP techniques across various convolutional neural networks used for radiological image analysis.",
        "keywords": "XAI, Healthcare AI, Medical Imaging, SHAP",
        "citation_count": 8
    },
    # Psychology / Medicine
    {
        "title": "The Impact of Social Media on Adolescent Mental Health",
        "author": "Emma Watson, James Miller",
        "year": "2022",
        "department": "Psychology",
        "abstract": "A longitudinal study tracking 2,000 teenagers over three years to determine the correlation between screen time and anxiety levels. Results indicate a significant increase in depressive symptoms associated with excessive social media use.",
        "keywords": "Mental Health, Social Media, Adolescent Psychology",
        "citation_count": 120
    },
    {
        "title": "Cognitive Behavioral Therapy vs Pharamacological Intervention for Insomnia",
        "author": "Dr. Linda Brown",
        "year": "2023",
        "department": "Psychology",
        "abstract": "This randomized controlled trial compares the long-term effectiveness of CBT-I against traditional sedative-hypnotics. Evidence suggests CBT-I provides more sustainable recovery from chronic sleep disorders.",
        "keywords": "Insomnia, CBT, Psychology, Clinical Trials",
        "citation_count": 56
    },
    # Engineering
    {
        "title": "Structural Integrity of 3D Printed Carbon Fiber Composites",
        "author": "Kenji Yamamoto, David Chen",
        "year": "2024",
        "department": "Engineering",
        "abstract": "An investigation into the tensile strength and durability of additive-manufactured carbon fiber components. We test various printing orientations and their impact on mechanical performance in aerospace applications.",
        "keywords": "3D Printing, Carbon Fiber, Material Science, Engineering",
        "citation_count": 3
    },
    {
        "title": "Renewable Energy Integration in Smart Grid Architectures",
        "author": "Elena Rossi",
        "year": "2023",
        "department": "Engineering",
        "abstract": "This paper presents a decentralized control strategy for managing fluctuating power inputs from solar and wind sources within a smart grid. We utilize blockchain for transparent energy credit distribution.",
        "keywords": "Renewable Energy, Smart Grid, Blockchain, Engineering",
        "citation_count": 34
    },
    {
        "title": "Autonomous Underwater Vehicles for Deep Sea Exploration",
        "author": "Michael Stone, Sophia Liu",
        "year": "2024",
        "department": "Engineering",
        "abstract": "Design and deployment of a new class of AUVs capable of reaching depths of 10,000 meters. The vehicle utilizes advanced sonar and pressure-resistant materials for geological mapping.",
        "keywords": "Robotics, Deep Sea, AUV, Marine Engineering",
        "citation_count": 7
    },
    # Mixed / More entries to reach 30+
    {"title": "Deep Reinforcement Learning for Robotic Grasping", "author": "Chris Evans", "year": "2024", "department": "Computer Science", "abstract": "Training robots to grasp diverse objects using pixel-to-action reinforcement learning policies.", "keywords": "Robotics, RL, AI", "citation_count": 15},
    {"title": "Climate Change Impacts on Tropical Biodiversity", "author": "Alice Green", "year": "2021", "department": "Medicine", "abstract": "Analyzing the extinction risks of endemic species in the Amazon rainforest due to rising global temperatures.", "keywords": "Climate Change, Biology, Ecology", "citation_count": 89},
    {"title": "Next-Generation Batteries for Electric Vehicles", "author": "John Doe", "year": "2023", "department": "Engineering", "abstract": "A review of solid-state battery technology and its potential to replace lithium-ion in the automotive industry.", "keywords": "Batteries, EV, Engineering", "citation_count": 42},
    {"title": "Neural Networks for Seismic Activity Prediction", "author": "Jane Smith", "year": "2024", "department": "Computer Science", "abstract": "Using LSTM networks to identify precursor patterns in seismic data for early earthquake warning systems.", "keywords": "Geology, LSTM, AI", "citation_count": 5},
    {"title": "The Role of Gut Microbiota in Human Metabolism", "author": "Dr. House", "year": "2022", "department": "Medicine", "abstract": "Investigating how bacterial colonies in the digestive tract influence obesity and diabetes risk.", "keywords": "Microbiology, Medicine, Health", "citation_count": 67},
    {"title": "Quantum Computing Algorithms for Cryptography", "author": "Richard Feynman", "year": "2023", "department": "Computer Science", "abstract": "Exploring Shor's algorithm and its implications for modern RSA encryption security.", "keywords": "Quantum, Security, Algorithms", "citation_count": 110},
    {"title": "Urban Planning and High-Speed Rail Integration", "author": "Frank Lloyd Wright", "year": "2020", "department": "Engineering", "abstract": "Strategies for designing walkable cities around mass transit hubs to reduce carbon footprints.", "keywords": "Urbanism, Transport, Engineering", "citation_count": 23},
    {"title": "Machine Learning in Algorithmic Trading", "author": "Warren Buffett", "year": "2024", "department": "Computer Science", "abstract": "Applying sentiment analysis to financial news for predicting stock market volatility.", "keywords": "Finance, ML, Search", "citation_count": 31},
    {"title": "Pediatric Neurology and Early Developmental Stages", "author": "Jean Piaget", "year": "2021", "department": "Psychology", "abstract": "Monitoring brain activity in infants during social interaction tasks.", "keywords": "Developmental, Brain, Psychology", "citation_count": 44},
    {"title": "Wireless Power Transfer for Implantable Devices", "author": "Nikola Tesla", "year": "2023", "department": "Engineering", "abstract": "Developing efficient electromagnetic induction methods for charging pacemakers through the skin.", "keywords": "Induction, Medical, Engineering", "citation_count": 18},
    {"title": "Hybrid Cloud Architectures for Enterprise Data", "author": "Satya Nadella", "year": "2024", "department": "Computer Science", "abstract": "Bridging on-premise infrastructure with public cloud services for elastic scalability.", "keywords": "Cloud, IT, Systems", "citation_count": 9},
    {"title": "Psychological Effects of Remote Work Isolation", "author": "Carl Jung", "year": "2022", "department": "Psychology", "abstract": "Analysis of office worker sentiment during the shift to full-time remote settings.", "keywords": "Remote Work, Psychology, Sociology", "citation_count": 37},
    {"title": "Sustainable Agriculture through Precision Farming", "author": "George Washington Carver", "year": "2023", "department": "Engineering", "abstract": "Using IoT sensors and drone imagery to optimize pesticide and water usage in large-scale farming.", "keywords": "IoT, Agriculture, Drones", "citation_count": 55},
    {"title": "Natural Language Processing for Ancient Artifact Matching", "author": "Indiana Jones", "year": "2024", "department": "Computer Science", "abstract": "Translating forgotten dialects using modern large language models trained on multiple script systems.", "keywords": "NLP, Archeology, BERT", "citation_count": 2},
    {"title": "Bio-Inspired Materials for Soft Robotics", "author": "Leonardo da Vinci", "year": "2023", "department": "Engineering", "abstract": "Creating robotic joints modeled after human muscle fibers for flexible motion.", "keywords": "Bio-Design, Robotics, Engineering", "citation_count": 14},
    {"title": "Cancer Immunotherapy: Targeted T-Cell Treatments", "author": "Dr. Watson", "year": "2024", "department": "Medicine", "abstract": "Engineering lymphocytes to recognize and eliminate metastatic cells in the blood stream.", "keywords": "Oncology, Medicine, Genetics", "citation_count": 88},
    {"title": "Edge Computing for Real-time Traffic Management", "author": "Elon Musk", "year": "2024", "department": "Computer Science", "abstract": "Processing camera data at the intersection to reduce latency in traffic light adjustments.", "keywords": "Smart City, Edge, AI", "citation_count": 4},
    {"title": "Stress Response and the Human HPA Axis", "author": "Sigmund Freud", "year": "2021", "department": "Psychology", "abstract": "Measuring cortisol levels in first responders during high-stress simulations.", "keywords": "Stress, Biology, Psychology", "citation_count": 71},
    {"title": "Nanocarriers for Targeted Drug Delivery", "author": "Marie Curie", "year": "2023", "department": "Medicine", "abstract": "Designing lipid-based nanoparticles that release medication only when triggered by pH changes.", "keywords": "Nanotech, Pharmacology, Medicine", "citation_count": 92},
    {"title": "Vertical Farming: The Future of Urban Food", "author": "Norman Borlaug", "year": "2022", "department": "Engineering", "abstract": "Hydroponic and aeroponic systems for growing crops within city skyscrapers.", "keywords": "Sustainability, Food, Engineering", "citation_count": 29},
    {"title": "Cybersecurity Threats in IoT Ecosystems", "author": "Kevin Mitnick", "year": "2024", "department": "Computer Science", "abstract": "Identifying vulnerabilities in smart home devices that lead to large-scale botnet attacks.", "keywords": "Security, IoT, Hacking", "citation_count": 13},
    {"title": "Human-Robot Interaction in Elder Care", "author": "Asimov", "year": "2023", "department": "Psychology", "abstract": "Studying the emotional attachment of seniors to companion robots in assisted living facilities.", "keywords": "HRI, Elder Care, Psychology", "citation_count": 21}
]

def clear_data():
    print("🗑️ Clearing existing data...")
    
    # 1. Clear Uploads folder
    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
    if os.path.exists(uploads_dir):
        shutil.rmtree(uploads_dir)
    os.makedirs(uploads_dir, exist_ok=True)
    print(" -> Uploads folder cleared.")

    # 2. Recreate Qdrant collection
    print(" -> Resetting Qdrant collection...")
    # Re-triggering _ensure_collection should work if we delete it first
    try:
        vector_db.client.delete_collection(settings.COLLECTION_NAME)
    except:
        pass
    vector_db._ensure_collection()
    print(" -> Qdrant collection reset.")

    # 3. Clear SQLite papers table
    db = SessionLocal()
    try:
        db.execute(text("DELETE FROM papers"))
        db.commit()
        print(" -> SQLite 'papers' table cleared.")
    except Exception as e:
        print(f" -> Error clearing SQLite: {e}")
        db.rollback()
    finally:
        db.close()

def seed_data():
    print(f"🌱 Seeding {len(DUMMY_PAPERS)} dummy papers...")
    db = SessionLocal()
    
    try:
        for data in DUMMY_PAPERS:
            # Create DB entry
            db_paper = Paper(
                title=data["title"],
                author=data["author"],
                year=data["year"],
                abstract=data["abstract"],
                department=data["department"],
                keywords=data["keywords"],
                citation_count=data["citation_count"],
                file_path="dummy/path.pdf" # Placeholder
            )
            db.add(db_paper)
            db.commit()
            db.refresh(db_paper)
            
            # Generate Embeddings
            print(f" -> Embedding: {db_paper.title}")
            title_vec = embedding_service.get_embedding(db_paper.title)
            abstract_vec = embedding_service.get_embedding(db_paper.abstract)
            
            # Save to Qdrant
            vector_db.upsert_paper(
                paper_id=db_paper.id,
                vectors={
                    "title": title_vec,
                    "abstract": abstract_vec
                },
                metadata={
                    "title": db_paper.title,
                    "author": db_paper.author,
                    "year": db_paper.year,
                    "abstract": db_paper.abstract,
                    "department": db_paper.department,
                    "citation_count": db_paper.citation_count
                }
            )
        
        print("✅ Seeding complete!")
        
    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    clear_data()
    seed_data()
