"""
generate_dummy_pdfs.py — Generates realistic thesis/capstone PDF files using reportlab.
Run: pip install reportlab && python generate_dummy_pdfs.py
Output: PDF files placed in the uploads/ folder.
"""
import os

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, PageBreak
    from reportlab.lib import colors
except ImportError:
    print("reportlab not found. Installing...")
    os.system("pip install reportlab")
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, PageBreak
    from reportlab.lib import colors

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

PAPERS = [
    {
        "filename": "dummy_iot_ids_thesis.pdf",
        "title": "Deep Learning-Based Intrusion Detection System for IoT Networks in Smart Home Environments",
        "degree": "Bachelor of Science in Computer Science",
        "program": "BSCS",
        "type": "Thesis",
        "authors": "Juan Miguel Santos\nMaria Angelica Reyes\nPaolo Emmanuel Cruz",
        "institution": "University of Lumia",
        "department": "Department of Computer Science",
        "year": "2023",
        "abstract": (
            "The proliferation of Internet of Things (IoT) devices in smart home environments has introduced "
            "significant cybersecurity challenges. Traditional rule-based intrusion detection systems (IDS) "
            "often fail to adapt to the evolving threat landscape. This study proposes a deep learning-based "
            "IDS leveraging Long Short-Term Memory (LSTM) networks to detect anomalous network traffic in "
            "real-time. The system was trained on the CICIDS2017 dataset augmented with synthetic IoT traffic. "
            "Results demonstrate a detection accuracy of 97.4% with a false-positive rate of 1.2%, "
            "outperforming conventional machine learning approaches including Random Forest and SVM. "
            "The findings establish LSTM-based IDS as a viable and scalable solution for consumer IoT security."
        ),
        "keywords": "deep learning, LSTM, intrusion detection, IoT, cybersecurity, smart home, network anomaly",
        "introduction": (
            "The rapid adoption of IoT devices has transformed modern residences into interconnected ecosystems "
            "capable of automating daily tasks. However, this connectivity introduces a broader attack surface "
            "that traditional network security mechanisms are ill-equipped to handle. Unlike enterprise environments, "
            "smart home networks often lack dedicated security infrastructure, making them prime targets for "
            "cyberattacks including botnet propagation, man-in-the-middle attacks, and data exfiltration. "
            "This research addresses the need for intelligent, adaptive intrusion detection tailored for IoT "
            "environments by leveraging the temporal modeling capabilities of deep recurrent neural networks. "
            "Specifically, we investigate the application of LSTM architectures to model normal network behavior "
            "and detect deviations that indicate malicious activity, without relying on predefined attack signatures."
        ),
        "methodology": (
            "The proposed system follows a three-stage pipeline: data collection and preprocessing, model training, "
            "and real-time inference. Network traffic was captured from a simulated smart home testbed comprising "
            "15 heterogeneous IoT devices. The CICIDS2017 benchmark dataset was used as supplementary training "
            "data. Features were extracted using CICFlowMeter, yielding 78 traffic flow attributes. "
            "An LSTM network with two stacked recurrent layers (128 and 64 units) and a dropout rate of 0.3 "
            "was trained using the Adam optimizer with a binary cross-entropy loss function. The dataset was "
            "split 70/15/15 for training, validation, and testing respectively. Class imbalance was addressed "
            "using SMOTE oversampling on minority attack classes."
        ),
        "results": (
            "The LSTM-based IDS achieved an overall detection accuracy of 97.4% on the test set, with precision "
            "of 96.8%, recall of 97.9%, and F1-score of 97.3%. The false positive rate was maintained at 1.2%, "
            "significantly lower than the baseline Random Forest model (FPR: 4.7%) and SVM (FPR: 3.1%). "
            "Per-class analysis revealed near-perfect detection for DoS and Port Scan attacks (F1 > 0.98), "
            "with slightly lower performance on Web Attacks (F1: 0.91) due to polymorphic payload variations. "
            "End-to-end inference latency averaged 47ms on a Raspberry Pi 4, validating practical deployment "
            "feasibility in resource-constrained edge environments."
        ),
        "conclusion": (
            "This thesis demonstrates that LSTM-based deep learning models can effectively detect intrusions in "
            "IoT smart home networks with high accuracy and low false-positive rates. The proposed system "
            "outperforms traditional machine learning baselines while maintaining deployment feasibility on "
            "edge hardware. Future work will explore federated learning to enable privacy-preserving distributed "
            "IDS across multiple smart home networks without centralizing sensitive traffic data."
        ),
    },
    {
        "filename": "dummy_student_performance_thesis.pdf",
        "title": "Predicting Student Academic Performance Using Ensemble Machine Learning in a Philippine University Setting",
        "degree": "Bachelor of Science in Information Systems",
        "program": "BSIS",
        "type": "Thesis",
        "authors": "Leilani Delos Santos\nKristoffer James Villanueva",
        "institution": "University of Lumia",
        "department": "Department of Information Systems",
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
        "keywords": "machine learning, ensemble methods, academic performance, student prediction, early alert system",
        "introduction": (
            "Student retention and academic success are among the foremost priorities in higher education "
            "management. Philippine universities face persistent challenges in identifying students at risk of "
            "academic failure before it is too late for meaningful intervention. Traditional threshold-based "
            "systems that flag students only after examination failures are fundamentally reactive. "
            "This study proposes a proactive, data-driven approach using ensemble machine learning to predict "
            "semester-end academic performance as early as the midterm period. By synthesizing behavioral "
            "indicators (e.g., class attendance, library usage), social factors (e.g., commute time, "
            "outside employment), and historical academic records, the system enables faculty advisors to "
            "intervene with at-risk students in a timely and targeted manner."
        ),
        "methodology": (
            "Student data from AY 2018-2021 was collected with institutional ethics approval, covering "
            "1,200 undergraduate students across four colleges. Twenty-three predictor features were selected "
            "through Recursive Feature Elimination (RFE). Three base classifiers — Gradient Boosting Machines "
            "(GBM), Random Forest (RF), and k-Nearest Neighbors (kNN) — were trained independently and combined "
            "using a soft-voting ensemble strategy. Hyperparameter optimization was performed via 5-fold "
            "cross-validated grid search. Performance was evaluated using accuracy, precision, recall, F1-score, "
            "and AUC-ROC. A leave-one-year-out validation scheme assessed temporal generalizability."
        ),
        "results": (
            "The ensemble model achieved 89.7% accuracy with F1-score of 0.88, outperforming GBM alone (86.2%), "
            "RF alone (84.9%), and kNN alone (78.3%). AUC-ROC for the ensemble was 0.947. Feature importance "
            "analysis identified cumulative GPA (prior semesters), midterm examination scores, and class "
            "attendance rate as the three most predictive features. The web dashboard deployed across two "
            "pilot colleges showed a 31% reduction in un-intervened at-risk cases during the validation semester, "
            "according to faculty feedback surveys."
        ),
        "conclusion": (
            "The proposed ensemble framework reliably predicts at-risk students with high accuracy in a "
            "Philippine university context. The accompanying faculty dashboard translates model outputs into "
            "actionable insights without requiring technical expertise from end-users. Future directions "
            "include incorporating real-time learning management system (LMS) data and extending the model "
            "to graduate education programs."
        ),
    },
    {
        "filename": "dummy_linguacheck_capstone.pdf",
        "title": "LinguaCheck: An Automated Grammar and Style Checker for Filipino-English Academic Writing Using NLP",
        "degree": "Bachelor of Science in Information Technology",
        "program": "BSIT",
        "type": "Capstone Project",
        "authors": "Alicia Fernandez\nRonaldo Macaraeg\nStephanie Anne Tan\nJerome Aquino",
        "institution": "University of Lumia",
        "department": "Department of Information Technology",
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
        "keywords": "NLP, BERT, grammar checking, code-switching, Filipino-English, academic writing, SUS",
        "introduction": (
            "Academic writing in Philippine higher education is characterized by extensive code-switching, "
            "the blending of Filipino (Tagalog) and English within single documents or even sentences. "
            "Existing grammar checker tools such as Grammarly and Microsoft Editor are trained on standardized "
            "monolingual English corpora and consequently fail to handle the linguistic nuances of Filipino-English "
            "mixed text. Errors involving Taglish grammar patterns, Filipino article misuse in English sentences, "
            "and culturally-specific academic phrasing are routinely missed or incorrectly flagged. "
            "This capstone project develops LinguaCheck to bridge this gap by fine-tuning BERT on a locally "
            "constructed corpus and deploying it as an accessible web-based writing tool for Filipino undergraduates."
        ),
        "methodology": (
            "A corpus of 15,000 annotated Filipino-English academic paragraphs was assembled from undergraduate "
            "thesis submissions with author permission, spanning five departments. Ten error categories were "
            "defined in collaboration with Filipino language and writing instructors. BERT-base-multilingual-cased "
            "was fine-tuned using a token classification (NER-style) objective with error span labeling. "
            "Training was conducted on Google Colab Pro with an A100 GPU over 8 epochs. The web frontend "
            "was built using Vue.js and communicates with the FastAPI-based inference backend via REST API. "
            "Usability evaluation followed the System Usability Scale (SUS) methodology with 60 participants "
            "from the College of Arts and Sciences and the College of Engineering."
        ),
        "results": (
            "LinguaCheck demonstrated 84.3% precision and 81.7% recall across all error categories. "
            "Subject-verb agreement errors had the highest detection rate (precision: 92.1%), while "
            "stylistic ambiguity detection was the weakest category (precision: 71.4%). "
            "The SUS score of 83.4 falls in the 'Excellent' category (Bangor et al., 2009). "
            "Comparative evaluation against Grammarly showed LinguaCheck outperforming on Taglish-specific "
            "errors by a margin of 34.7 percentage points in F1. Faculty reviewers rated the system highly "
            "for contextual relevance in a Philippine academic setting."
        ),
        "conclusion": (
            "LinguaCheck successfully addresses a significant gap in automated writing support for "
            "Filipino-English bilingual students. By fine-tuning a multilingual BERT model on a locally "
            "constructed corpus, the system achieves competitive accuracy on culturally-relevant error categories "
            "while providing an accessible interface. Future development will expand the error taxonomy, "
            "incorporate citation style checking for APA and IEEE formats common in Philippine theses, "
            "and explore mobile accessibility."
        ),
    },
    {
        "filename": "dummy_smartbridge_capstone.pdf",
        "title": "SmartBridge: An IoT-Based Structural Health Monitoring System for Pedestrian Bridges",
        "degree": "Bachelor of Science in Computer Engineering",
        "program": "BSCpE",
        "type": "Capstone Project",
        "authors": "Rafael Antonio Navarro\nJessa Marie Ocampo\nDennis Alcantara",
        "institution": "University of Lumia",
        "department": "Department of Computer Engineering",
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
        "keywords": "IoT, structural health monitoring, Raspberry Pi, MQTT, edge computing, bridge safety, embedded systems",
        "introduction": (
            "The Philippines' aging urban infrastructure, particularly pedestrian bridges in metropolitan areas, "
            "poses significant public safety risks. Manual inspection cycles are infrequent, expensive, and "
            "unable to provide continuous structural condition data. Recent advances in low-cost IoT sensing "
            "and edge computing offer an opportunity to deploy persistent, real-time monitoring systems at "
            "a fraction of traditional civil engineering instrumentation costs. SmartBridge leverages "
            "off-the-shelf sensors (ADXL345 accelerometers, HX711 strain gauge amplifiers) with a Raspberry Pi "
            "4 edge node to continuously measure structural vibration, stress, and deformation. "
            "Alert thresholds informed by AASHTO LRFD guidelines ensure that anomalies triggering safety "
            "concerns are promptly communicated to infrastructure managers via mobile notifications."
        ),
        "methodology": (
            "The SmartBridge system comprises three layers: a sensor layer (accelerometers + strain gauges), "
            "an edge layer (Raspberry Pi 4 running Python-based data acquisition and anomaly detection), "
            "and a cloud layer (MQTT broker + Node-RED dashboard + Telegram alert bot). "
            "Sensor sampling was performed at 200 Hz for vibration and 10 Hz for strain. "
            "A sliding-window peak detection algorithm identified anomalous vibration events. "
            "Field deployment was conducted on Marikina Shoe Expo Footbridge with DPWH coordination. "
            "Data was collected over 60 days under varying load conditions including pedestrian peak hours "
            "and extreme weather events. System reliability, latency, and energy consumption were measured "
            "against pre-defined KPIs."
        ),
        "results": (
            "Over 60 operational days, SmartBridge achieved 99.1% uptime with two planned maintenance windows. "
            "Mean alert latency from sensor event to Telegram notification was 2.7 seconds (target: <3s). "
            "Three genuine anomalous vibration events were captured during the monitoring period, "
            "all corresponding to verified high-load pedestrian crowding events. "
            "No false-positive structural alerts were generated. Power consumption averaged 4.1W, "
            "enabling solar-assisted operation in future deployments. Total hardware cost per node "
            "was estimated at PHP 8,500 (~USD 150), demonstrating significant cost advantage over "
            "commercial SHM systems (typically USD 5,000-50,000 per sensor node)."
        ),
        "conclusion": (
            "SmartBridge demonstrates that IoT-based structural health monitoring is technically feasible "
            "and economically viable for pedestrian bridge infrastructure in a developing-country context. "
            "The system's low cost, sub-3-second alert latency, and 99.1% uptime validate its practical "
            "deployment potential. Future work will integrate machine learning for predictive maintenance "
            "scheduling and extend deployment to vehicular bridges with heavier dynamic load requirements."
        ),
    },
]


def build_styles():
    base = getSampleStyleSheet()
    styles = {
        "institution": ParagraphStyle("institution", parent=base["Normal"], fontSize=12, leading=16, alignment=TA_CENTER),
        "degree": ParagraphStyle("degree", parent=base["Normal"], fontSize=11, leading=14, alignment=TA_CENTER, textColor=colors.HexColor("#555555")),
        "type_label": ParagraphStyle("type_label", parent=base["Normal"], fontSize=11, leading=14, alignment=TA_CENTER, textColor=colors.HexColor("#1a6c37"), bold=True),
        "title": ParagraphStyle("title", parent=base["Normal"], fontSize=17, leading=22, alignment=TA_CENTER, bold=True, spaceAfter=12),
        "authors": ParagraphStyle("authors", parent=base["Normal"], fontSize=11, leading=16, alignment=TA_CENTER, textColor=colors.HexColor("#333333")),
        "year": ParagraphStyle("year", parent=base["Normal"], fontSize=10, leading=14, alignment=TA_CENTER, textColor=colors.HexColor("#777777")),
        "section_header": ParagraphStyle("section_header", parent=base["Normal"], fontSize=13, leading=18, bold=True, spaceAfter=6, spaceBefore=14, textColor=colors.HexColor("#1a3a6c")),
        "body": ParagraphStyle("body", parent=base["Normal"], fontSize=10.5, leading=17, alignment=TA_JUSTIFY, spaceAfter=8),
        "keywords_label": ParagraphStyle("kw_label", parent=base["Normal"], fontSize=10, leading=14, bold=True),
        "keywords_text": ParagraphStyle("kw_text", parent=base["Normal"], fontSize=10, leading=14, textColor=colors.HexColor("#444444")),
    }
    return styles


def generate_pdf(paper: dict, output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        topMargin=2.5*cm,
        bottomMargin=2.5*cm,
        leftMargin=3*cm,
        rightMargin=3*cm
    )
    s = build_styles()
    story = []

    # ── TITLE PAGE ──
    story.append(Spacer(1, 1.5*cm))
    story.append(Paragraph(paper["institution"].upper(), s["institution"]))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(paper["department"], s["degree"]))
    story.append(Spacer(1, 0.8*cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1a3a6c")))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(f"A {paper['type']} Presented in Partial Fulfillment", s["degree"]))
    story.append(Paragraph(f"of the Requirements for the Degree of", s["degree"]))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(f"<b>{paper['degree']} ({paper['program']})</b>", s["type_label"]))
    story.append(Spacer(1, 1.2*cm))
    story.append(Paragraph(paper["title"], s["title"]))
    story.append(Spacer(1, 1.0*cm))
    story.append(HRFlowable(width="60%", thickness=0.7, color=colors.HexColor("#aaaaaa")))
    story.append(Spacer(1, 0.6*cm))
    story.append(Paragraph("Presented by:", s["degree"]))
    story.append(Spacer(1, 0.3*cm))
    for author in paper["authors"].split("\n"):
        story.append(Paragraph(f"<b>{author.strip()}</b>", s["authors"]))
    story.append(Spacer(1, 0.8*cm))
    story.append(Paragraph(paper["year"], s["year"]))
    story.append(PageBreak())

    # ── ABSTRACT ──
    story.append(Paragraph("Abstract", s["section_header"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")))
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph(paper["abstract"], s["body"]))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("<b>Keywords:</b>", s["keywords_label"]))
    story.append(Paragraph(paper["keywords"], s["keywords_text"]))
    story.append(Spacer(1, 1*cm))

    # ── BODY SECTIONS ──
    sections = [
        ("1. Introduction", "introduction"),
        ("2. Methodology", "methodology"),
        ("3. Results and Discussion", "results"),
        ("4. Conclusion", "conclusion"),
    ]
    for header, key in sections:
        story.append(Paragraph(header, s["section_header"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")))
        story.append(Spacer(1, 0.4*cm))
        story.append(Paragraph(paper[key], s["body"]))
        story.append(Spacer(1, 0.5*cm))

    doc.build(story)
    print(f"[PDF] Generated: {output_path}")


def main():
    for paper in PAPERS:
        out = os.path.join(UPLOAD_DIR, paper["filename"])
        generate_pdf(paper, out)
    print(f"\n✅ All {len(PAPERS)} PDFs generated in '{UPLOAD_DIR}/'")


if __name__ == "__main__":
    main()
