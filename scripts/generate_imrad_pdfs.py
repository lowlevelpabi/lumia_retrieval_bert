"""
generate_imrad_pdfs.py
Generates 25 dummy IMRAD-structured thesis PDFs for testing IMRAD section detection.
Run from project root: python scripts/generate_imrad_pdfs.py

Requires: pip install reportlab
"""
import os
import sys

try:
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
except ImportError:
    print("Installing reportlab...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab"])
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dummy_imrad_pdfs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

PAPERS = [
    {
        "title": "Plant Disease Detection Using Convolutional Neural Networks",
        "authors": "DELA CRUZ, MARIA S. | REYES, JUAN A.",
        "year": "2024", "dept": "Department of Computer Science", "degree": "BSCS",
        "keywords": "CNN, plant disease, deep learning, image classification",
        "abstract": "This study presents a CNN-based system for automated plant disease detection from leaf images. Using ResNet-50 on a dataset of 5,000 annotated images, the system achieved 93.4% accuracy, outperforming SVM-based baselines by 6.4%.",
        "introduction": "Agriculture is a critical sector of the Philippine economy, contributing nearly 10% to GDP. Early detection of leaf diseases such as Bacterial Blight, Powdery Mildew, and Late Blight can prevent up to 25% yield losses annually. Manual inspection by agronomists is slow and costly, motivating automation. This study aims to: (1) develop a CNN model for multi-class leaf disease classification; (2) evaluate its performance on a curated local dataset; (3) compare results with traditional machine learning classifiers.",
        "methods": "This study employed a ResNet-50 Convolutional Neural Network pretrained on ImageNet and fine-tuned on a custom dataset of 5,000 leaf images from the PlantVillage corpus. The dataset covers 10 disease categories. An 80/20 stratified split was used for training and validation. Data augmentation included horizontal flip, 15-degree rotation, and brightness jitter. The model was trained for 50 epochs using Adam optimizer (lr=0.001) with early stopping (patience=5). A confusion matrix, precision, recall, and F1-score were computed for evaluation. GPU: NVIDIA GTX 1060.",
        "results": "The ResNet-50 model achieved 93.4% overall accuracy on the validation set. Precision was 92.1%, recall 93.8%, and F1-score 92.9%. Per-class accuracy ranged from 87% (Early Blight vs Late Blight confusion) to 97% (Powdery Mildew). Training converged at epoch 38. Comparison with SVM (87%) and KNN (79%) classifiers confirmed the superiority of the CNN approach.",
        "discussion": "The 93.4% accuracy confirms CNNs as the most effective approach for automated plant disease detection. The main source of error is visual similarity between Early Blight and Late Blight, a known challenge in the domain. Data augmentation significantly improved generalization. Future work should explore Vision Transformers and domain-specific pretraining using Philippine crop datasets.",
    },
    {
        "title": "Smart Attendance System Using Facial Recognition and FaceNet",
        "authors": "SANTOS, JOSE B. | GARCIA, ANNA C.",
        "year": "2024", "dept": "Department of Information Technology", "degree": "BSIT",
        "keywords": "facial recognition, FaceNet, attendance system, SVM",
        "abstract": "This paper presents a real-time smart attendance system using FaceNet embeddings and SVM classification deployed on Raspberry Pi 4, achieving 96.2% recognition accuracy under controlled conditions.",
        "introduction": "Proxy attendance and manual recording errors are persistent problems in higher education institutions. Biometric-based systems using fingerprint scanners have been adopted but require physical contact. Facial recognition offers a contactless alternative. This study proposes a FaceNet-based system integrated with a web dashboard for real-time attendance logging, targeting 200 students at Cavite State University Imus Campus.",
        "methods": "FaceNet (Inception ResNet V1) was employed to generate 128-dimensional face embeddings. An SVM classifier with an RBF kernel was trained on a dataset of 2,000 face images (200 students × 10 images). Images were captured under three lighting conditions. The system was deployed on Raspberry Pi 4 (4GB RAM) with a Logitech C920 webcam. Evaluation metrics: accuracy, False Acceptance Rate (FAR), False Rejection Rate (FRR), and average processing time per recognition event.",
        "results": "The system achieved 96.2% recognition accuracy under controlled lighting. FAR was 0.3% and FRR was 3.5%. Average processing time was 350ms per recognition event, suitable for real-time use. Performance dropped to 88% under low-light conditions. The web dashboard correctly logged attendance events with 99.1% database write success rate.",
        "discussion": "FaceNet-based recognition meets practical accuracy requirements for attendance systems. Low-light sensitivity is the primary limitation, attributed to insufficient IR-compensated training data. Raspberry Pi 4 computational limits become apparent at >5 simultaneous recognition events. Future work should incorporate infrared cameras and multi-face detection for classroom deployment.",
    },
    {
        "title": "Sentiment Analysis of Student Feedback Using BERT",
        "authors": "LARA, PATRICIA M. | NAVARRO, CARLO J.",
        "year": "2023", "dept": "Department of Computer Science", "degree": "BSCS",
        "keywords": "BERT, sentiment analysis, NLP, student feedback, transformer",
        "abstract": "This study applies BERT for sentiment analysis of student course evaluations at CvSU, achieving 91.7% accuracy and enabling automated identification of positive and negative instructional feedback patterns.",
        "introduction": "Student course evaluations generate large volumes of unstructured text that are often analyzed manually, introducing bias and delay. Natural Language Processing (NLP) can automate sentiment classification. This study fine-tunes BERT on a dataset of 8,500 student feedback entries to classify sentiments as Positive, Neutral, or Negative, supporting data-driven faculty performance evaluation.",
        "methods": "BERT-base-uncased was fine-tuned using the HuggingFace Transformers library on a dataset of 8,500 course evaluation comments collected from CvSU's Student Evaluation System (SES). Labels were assigned by two human annotators with inter-rater agreement of Cohen's Kappa = 0.83. A stratified 70/15/15 train/validation/test split was used. Hyperparameters: batch size 32, learning rate 2e-5, 5 epochs, max token length 128.",
        "results": "BERT achieved 91.7% accuracy on the test set. Macro F1 was 0.90. Positive class precision was 94%, Neutral 87%, and Negative 93%. BERT outperformed baseline logistic regression (78%) and BiLSTM (85%). The model also produced interpretable attention maps highlighting key sentiment-bearing phrases.",
        "discussion": "BERT's contextual embeddings significantly improve feedback sentiment classification over traditional ML methods. Neutral class confusion with Positive remains a challenge due to polite but critical feedback patterns common in Filipino academic culture. Future integration with the university's evaluation portal would enable real-time sentiment dashboards.",
    },
    {
        "title": "E-Commerce Recommendation System Using Collaborative Filtering",
        "authors": "MENDOZA, RYAN P. | TORRES, LISA K.",
        "year": "2024", "dept": "Department of Information Systems", "degree": "BSIS",
        "keywords": "collaborative filtering, recommendation system, matrix factorization, e-commerce",
        "abstract": "This study implements a collaborative filtering recommendation engine using Singular Value Decomposition (SVD) for a local e-commerce platform, achieving RMSE of 0.94 and increasing click-through rate by 18%.",
        "introduction": "Online shoppers face information overload as product catalogs expand. Recommendation systems address this by personalizing the shopping experience. Collaborative filtering leverages user-item interaction patterns without requiring product content knowledge. This study develops and evaluates a recommendation engine for a Cavite-based online handicraft marketplace with 1,200 users and 3,500 products.",
        "methods": "Singular Value Decomposition (SVD) via the Surprise library was implemented on an implicit feedback matrix of 45,000 user-item interactions. Cross-validation used a 5-fold strategy. Hyperparameter tuning: n_factors in [50, 100, 150], regularization in [0.02, 0.05, 0.1]. Evaluation metrics: Root Mean Squared Error (RMSE), Mean Absolute Error (MAE), Precision@10, and Recall@10. A/B testing was conducted with 50 active users over 2 weeks.",
        "results": "SVD achieved RMSE of 0.94 and MAE of 0.71 on the test set. Precision@10 was 0.43 and Recall@10 was 0.38. The A/B test showed an 18% increase in click-through rate versus the non-personalized control group. Best hyperparameters: n_factors=100, regularization=0.05.",
        "discussion": "SVD collaborative filtering provides meaningful recommendation quality for a sparse interaction matrix. The cold-start problem for new users remains unresolved and is the chief limitation. Future work should explore hybrid approaches combining SVD with content-based filtering using product category embeddings.",
    },
    {
        "title": "IoT-Based Smart Irrigation System for Urban Farming",
        "authors": "PASCUAL, JEROME O. | VILLANUEVA, GRACE T.",
        "year": "2023", "dept": "Department of Computer Engineering", "degree": "BSCpE",
        "keywords": "IoT, irrigation, smart farming, Arduino, soil moisture sensor",
        "abstract": "This study develops an IoT-based automated irrigation system using Arduino, soil moisture sensors, and a mobile app, reducing water consumption by 34% while maintaining comparable crop yield.",
        "introduction": "Urban farming in the Philippines faces water management challenges due to irregular rainfall and reliance on manual irrigation. Over-irrigation wastes resources; under-irrigation reduces yield. IoT-enabled precision irrigation offers a data-driven solution. This study designs and evaluates an automated irrigation system for a 200 sqm rooftop garden at Imus City Hall, targeting water efficiency improvement.",
        "methods": "The system comprised Arduino Mega 2560 microcontroller, capacitive soil moisture sensors (4 units), a 12V solenoid valve, DHT22 temperature-humidity sensor, and a 4G GSM module. A threshold-based irrigation algorithm activates watering when soil moisture drops below 35%. A Flutter mobile app provides real-time sensor monitoring and manual override. Data was logged over 90 days (June–August 2023). Evaluation: daily water usage (liters), soil moisture stability (variance), and crop yield (kg/sqm).",
        "results": "The IoT system reduced average daily water consumption from 85L to 56L (34% reduction). Soil moisture variance decreased from ±12% to ±4%, indicating stable crop hydration. Crop yield was 2.1 kg/sqm vs. 2.0 kg/sqm for the manual control plot (not statistically significant, p=0.31). System uptime was 97.2% over the 90-day evaluation period.",
        "discussion": "The 34% water reduction demonstrates meaningful efficiency gains without yield compromise. The non-significant yield difference suggests that threshold-based irrigation is comparable to experienced manual irrigation for common crops. Future work should integrate weather API forecasting to pre-emptively adjust thresholds and evaluate multi-crop scenarios.",
    },
    {
        "title": "Online Scheduling System for Academic Consultations Using Dijkstra's Algorithm",
        "authors": "CRUZ, MARK A. | DIZON, SHEILA R.",
        "year": "2024", "dept": "Department of Information Technology", "degree": "BSIT",
        "keywords": "scheduling, Dijkstra, consultation system, graph algorithm, web system",
        "abstract": "This study presents an online consultation scheduling system that uses Dijkstra's algorithm to recommend the optimal available time slot for student-faculty consultations, reducing average wait time by 41%.",
        "introduction": "Inefficient consultation scheduling at CvSU leads to faculty overloading on certain days and student frustration. Walk-in systems create bottlenecks, and informal messaging lacks transparency. This study develops a web-based system with an intelligent scheduling engine that models faculty availability as a weighted graph and recommends optimal consultation slots using Dijkstra's shortest path algorithm.",
        "methods": "The system was developed using Laravel (PHP) backend and Vue.js frontend, deployed on a local server. Faculty schedules are modeled as a directed weighted graph where edge weights represent time-slot priority scores based on faculty preference, room availability, and load balance. Dijkstra's algorithm computes the minimum-cost available slot for each consultation request. The system was pilot-tested with 15 faculty members and 120 students over one semester.",
        "results": "Average consultation wait time was reduced from 2.3 days to 1.35 days (41.3% reduction). Faculty reported 82% satisfaction with schedule fairness (Likert scale survey). System response time for slot computation averaged 0.4 seconds. No scheduling conflicts were recorded during the pilot period. Student adoption rate reached 78% by the 4th week.",
        "discussion": "Graph-based scheduling with Dijkstra's algorithm effectively optimizes consultation slot allocation. The system scales linearly with faculty count. Manual override capability was the most requested feature and was added in iteration 3. Future work should incorporate machine learning to predict preferred time slots based on historical scheduling patterns.",
    },
    {
        "title": "Cyberbullying Detection on Social Media Using Machine Learning",
        "authors": "AQUINO, JANA L. | BAUTISTA, FELIX C.",
        "year": "2024", "dept": "Department of Computer Science", "degree": "BSCS",
        "keywords": "cyberbullying, text classification, SVM, NLP, social media",
        "abstract": "This study compares SVM, Random Forest, and LSTM classifiers for detecting cyberbullying in Filipino-English social media content, finding that SVM with TF-IDF features achieves the best F1-score of 88.3%.",
        "introduction": "Cyberbullying is a growing issue among Filipino youth, exacerbated by high social media usage rates. Platforms lack automated Filipino-language moderation. NLP-based detection can flag harmful content in real time. This study builds and compares classifiers on a dataset of 12,000 annotated Filipino-English (Taglish) social media posts.",
        "methods": "A dataset of 12,000 Taglish tweets and Facebook comments was collected and annotated into Bullying and Non-Bullying classes (60/40 split). Three classifiers were compared: SVM with TF-IDF (unigrams+bigrams), Random Forest with word2vec embeddings, and a Bidirectional LSTM. Preprocessing: lowercasing, stopword removal, code-mixed text normalization, and emoji-to-text conversion. Evaluation: F1-score, precision, recall, and 5-fold cross-validation.",
        "results": "SVM achieved the highest F1-score of 88.3% (precision 89.1%, recall 87.6%). Random Forest scored F1=85.7% and BiLSTM scored F1=87.1%. SVM training time was 12 seconds vs. LSTM's 4 hours. SVM misclassified sarcastic expressions as non-bullying in 7.4% of cases.",
        "discussion": "SVM with TF-IDF remains a strong baseline for short-text classification, outperforming even deep learning on this dataset size. Sarcasm and code-mixing are the primary error sources. The class imbalance (60/40) was addressed with SMOTE oversampling. Future work should explore mBERT and XLM-R for multilingual Filipino-English understanding.",
    },
    {
        "title": "Library Management System with QR Code-Based Book Tracking",
        "authors": "REYES, CRISTINA V. | SANTOS, MARK P.",
        "year": "2023", "dept": "Department of Information Systems", "degree": "BSIS",
        "keywords": "library system, QR code, book tracking, inventory, Django",
        "abstract": "This study develops a web-based library management system with QR code-based book tracking developed in Django, reducing average book retrieval time by 52% and inventory discrepancy by 78%.",
        "introduction": "The CvSU Imus Campus library relies on manual card-based borrowing records, resulting in frequent inventory discrepancies and slow book retrieval. A digitized library system with automated tracking can significantly improve efficiency. This study designs and implements a Django-based Library Management System (LMS) with QR code-based book identification for the campus library's 8,500-volume collection.",
        "methods": "The system was built using Django 4.2 (Python) with PostgreSQL as the database backend and Bootstrap 5 for the frontend. QR codes are generated using the qrcode library (one code per book copy). A Raspberry Pi 3 with a USB QR scanner serves as the circulation desk terminal. Modules include: catalog management, borrowing/return workflow, overdue tracking, and inventory audit. User acceptance testing was conducted with 5 librarians and 50 students over 4 weeks.",
        "results": "Average book retrieval time decreased from 4.2 minutes to 2.0 minutes (52% reduction). Inventory discrepancy rate dropped from 14% to 3.1% (78% improvement). Overdue detection accuracy was 100% compared to 73% for the manual system. System response time averaged 1.1 seconds. All 5 librarians rated system usability as 'Excellent' on the SUS scale (avg score: 87.4).",
        "discussion": "QR-based tracking combined with a digital workflow substantially improves library operations. The 3.1% remaining inventory discrepancy is attributed to unreturned books from before system adoption. Future enhancements should include RFID for hands-free scanning, integration with the university's student information system, and a student-facing mobile app for catalog browsing.",
    },
    {
        "title": "Real-Time Object Detection for Campus Security Using YOLOv8",
        "authors": "FLORES, DENNIS B. | CAMACHO, ROSE N.",
        "year": "2024", "dept": "Department of Computer Engineering", "degree": "BSCpE",
        "keywords": "object detection, YOLOv8, CCTV, campus security, deep learning",
        "abstract": "This study implements a real-time object detection system for campus perimeter security using YOLOv8, detecting unauthorized persons and abandoned objects with 91.8% mAP on a custom campus dataset.",
        "introduction": "Campus security monitoring at educational institutions relies heavily on human operators monitoring CCTV feeds, which is prone to fatigue and missed events. Automated object detection using deep learning can augment security staff by flagging suspicious activities. This study develops a YOLOv8-based detection system integrated with the CCTV infrastructure at CvSU Imus Campus.",
        "methods": "YOLOv8-medium was trained on a custom dataset of 3,200 annotated CCTV frames covering: Person, Bag (abandoned), Vehicle, and Restricted Area Intrusion classes. Annotation was done using Roboflow. Training: 100 epochs, image size 640×640, batch size 16, AdamW optimizer. The model was deployed on a Jetson Nano (4GB) connected to 4 IP cameras. Alerts are sent via email and SMS when confidence exceeds 0.7.",
        "results": "YOLOv8-medium achieved mAP@0.5 of 91.8% on the validation set. Person class AP was 95.1%; Abandoned Bag AP was 87.3%. Inference speed averaged 28 FPS on Jetson Nano, meeting real-time requirements. False positive rate was 4.2%. The system was stress-tested over 72 hours with zero crashes.",
        "discussion": "YOLOv8 provides robust real-time detection suitable for campus security deployment. Abandoned bag detection remains challenging due to class imbalance (only 12% of dataset). Nighttime performance degraded to mAP 79% due to insufficient low-light training data. Future work should incorporate night-vision training data and integrate with an access control system.",
    },
    {
        "title": "Predictive Analytics for Student At-Risk Detection Using Random Forest",
        "authors": "MIRANDA, ANNA J. | HERNANDEZ, RALPH S.",
        "year": "2023", "dept": "Department of Information Systems", "degree": "BSIS",
        "keywords": "predictive analytics, student at-risk, Random Forest, academic performance",
        "abstract": "This study builds a Random Forest classifier to predict at-risk students using enrollment, grade, and attendance data, achieving 87.5% accuracy and enabling early intervention programs.",
        "introduction": "Student dropout and academic failure are costly problems for universities. Early identification of at-risk students enables timely intervention. Traditional methods rely on reactive grade monitoring. This study develops a predictive model using machine learning on historical academic data from CvSU Imus Campus to classify students as At-Risk or Not-At-Risk as early as the 6th week of the semester.",
        "methods": "Features used: GWA from previous semester, attendance rate (%), number of incomplete grades, scholarship status, financial aid, and course load. Data covered 1,850 students from AY 2019-2022. Random Forest (100 estimators, max depth 10) was trained on a 75/25 train-test split. SMOTE oversampling addressed class imbalance (25% at-risk). Feature importance was extracted to inform counselor reports. SHAP values were computed for explainability.",
        "results": "Random Forest achieved 87.5% accuracy, precision 84.2%, recall 89.7%, F1 86.9%. The top 3 predictive features were: previous GWA (importance=0.41), attendance rate (0.28), and number of INC grades (0.19). 76 true at-risk students were identified in a live pilot during 2nd semester 2023, and 61 (80%) successfully completed the semester after intervention.",
        "discussion": "The model's 89.7% recall minimizes missed at-risk cases, the higher-priority error in academic intervention contexts. SHAP explanations enabled counselors to understand and trust the predictions. The 80% intervention success rate validates practical utility. Future work should incorporate real-time data integration with the university's SIS for automated early-warning alerts.",
    },
    {
        "title": "Automated Grading System for Essay Responses Using NLP",
        "authors": "AGUILA, SARAH M. | DELA TORRE, JAMES R.",
        "year": "2024", "dept": "Department of Computer Science", "degree": "BSCS",
        "keywords": "automated essay grading, NLP, cosine similarity, BERT, education technology",
        "abstract": "This study develops an automated essay grading system using BERT sentence embeddings and cosine similarity scoring, achieving 0.87 Pearson correlation with expert human graders.",
        "introduction": "Manual essay grading is time-consuming and subjective. Automated Essay Scoring (AES) systems can provide consistent, instant feedback. This study targets short-answer essay questions in STEM subjects at CvSU, where graders assess technical accuracy and conceptual understanding. The system compares student responses against model answers using semantic similarity.",
        "methods": "BERT sentence embeddings (bert-base-uncased, pooled CLS token) were used to encode both student responses and model answers. Cosine similarity between embeddings was mapped to a 0-10 score scale via linear regression trained on 500 expert-graded pairs. A rubric-alignment module penalizes off-topic responses using keyword overlap (Jaccard similarity). Dataset: 3,200 essay responses across 8 STEM courses.",
        "results": "The system achieved Pearson correlation r=0.87 with expert scores on the held-out test set. Mean absolute error was 0.71 points on a 10-point scale. Inter-rater agreement between system and human expert (Cohen's Kappa=0.79) was comparable to inter-human agreement (0.82). Processing time: 0.3 seconds per essay.",
        "discussion": "BERT-based semantic scoring outperforms TF-IDF cosine similarity (r=0.71) and keyword matching (r=0.58) for essay grading tasks. The main failure mode is factually correct responses phrased very differently from the model answer. Future work should fine-tune on domain-specific STEM corpora and incorporate factual consistency checking.",
    },
    {
        "title": "Flood Prediction System Using LSTM Neural Networks and Rainfall Data",
        "authors": "OCAMPO, RYAN T. | SALAZAR, DIANA P.",
        "year": "2023", "dept": "Department of Computer Science", "degree": "BSCS",
        "keywords": "LSTM, flood prediction, time series, rainfall, disaster risk reduction",
        "abstract": "This study implements an LSTM-based flood prediction model using 10 years of rainfall and water level data from Cavite Province, achieving 92.3% prediction accuracy 24 hours ahead of flood events.",
        "introduction": "Cavite Province experiences regular monsoon-driven flooding causing property damage and casualties. Current PAGASA forecasts lack local granularity. This study builds an LSTM neural network for Imus River flood prediction using historical rainfall and water level telemetry data, targeting 24-hour advance warning with high accuracy for local DRRMO use.",
        "methods": "Ten years (2013-2022) of 6-hourly rainfall data (mm) and river water level (m) from 3 PAGASA stations were used. Data preprocessing: linear interpolation for missing values, MinMax normalization. LSTM architecture: 2 stacked layers (128 and 64 units), dropout=0.2, lookback window=48 timesteps (12 days). Output: binary flood/no-flood classification for t+24h. Train/validation/test: 2013-2020/2021/2022. Evaluation: accuracy, precision, recall, F1, AUC-ROC.",
        "results": "LSTM achieved 92.3% accuracy, precision 88.7%, recall 94.1%, F1 91.3%, AUC-ROC 0.96. Compared to ARIMA (accuracy 79%) and persistence model (72%), LSTM demonstrated clear superiority. Average prediction lead time was 26.4 hours. The model predicted 14/15 flood events in 2022, missing one flash flood event caused by an isolated convective storm.",
        "discussion": "LSTM's ability to capture long-term temporal dependencies is critical for flood forecasting in a monsoon climate. The missed prediction was associated with a localized convective storm pattern not well-represented in training data. Future work should incorporate satellite rainfall estimates and real-time weather model outputs to handle such events.",
    },
    {
        "title": "Mobile Expense Tracker with Budget Anomaly Detection",
        "authors": "VILLAFUERTE, KYLA A. | RAMOS, JOHN G.",
        "year": "2024", "dept": "Department of Information Technology", "degree": "BSIT",
        "keywords": "mobile app, expense tracking, anomaly detection, Isolation Forest, Flutter",
        "abstract": "This study develops a Flutter-based mobile expense tracking application with Isolation Forest anomaly detection to flag unusual spending patterns, achieving 89.4% anomaly detection accuracy in user trials.",
        "introduction": "Personal financial management is a challenge for Filipino college students, many of whom lack formal budgeting skills. Mobile expense trackers exist but typically lack intelligent analysis. This study adds anomaly detection to a mobile expense tracker to proactively alert users when spending deviates significantly from their historical patterns, supporting financial literacy.",
        "methods": "A Flutter mobile application was developed for Android and iOS. The backend uses FastAPI (Python) with SQLite. Expense data is categorized into 8 categories (Food, Transport, Academic, etc.). Isolation Forest is applied on rolling 30-day spending vectors to detect outliers (contamination=0.1). The app was beta-tested with 40 CvSU students over 60 days. Evaluation: precision and recall of anomaly alerts vs. self-reported unexpected expenses.",
        "results": "Isolation Forest achieved 89.4% precision and 84.7% recall for anomaly detection against user self-reports. Users received an average of 2.3 alerts per month. 78% of users rated alerts as 'useful' or 'very useful'. Average session time increased 22% vs. a control app without anomaly alerts. App crash rate was 0.3% over 60 days.",
        "discussion": "Anomaly detection meaningfully enhances expense tracking utility by providing proactive insights rather than passive logging. False positives (10.6%) were mainly triggered by irregular but legitimate expenses like semester fees. Future work should allow user-defined category budgets as anomaly baselines and integrate with GCash/Maya transaction history APIs.",
    },
    {
        "title": "Traffic Flow Prediction Using Graph Neural Networks",
        "authors": "BERNARDINO, LEO C. | TUAZON, MICHELLE F.",
        "year": "2024", "dept": "Department of Computer Science", "degree": "BSCS",
        "keywords": "Graph Neural Networks, GNN, traffic prediction, Cavite, road network",
        "abstract": "This study applies a Graph Convolutional Network (GCN) on the Imus-Bacoor road network graph for traffic flow prediction, achieving a 15.2% improvement in RMSE over baseline LSTM models.",
        "introduction": "Traffic congestion in Cavite's urban corridors causes significant economic and environmental costs. Traditional prediction models treat roads independently, ignoring the spatial relationships in road networks. Graph Neural Networks (GNNs) can model these dependencies explicitly. This study constructs a road network graph from OpenStreetMap data and applies GCN-based traffic flow prediction for the Imus-Bacoor corridor.",
        "methods": "The road network of the Imus-Bacoor corridor was modeled as a directed weighted graph (147 nodes, 298 edges) extracted from OpenStreetMap. Speed and volume data from 12 CCTV-based sensors were aggregated at 15-minute intervals over 6 months. A Graph Convolutional Network with 2 convolutional layers and a GRU temporal module was implemented in PyTorch Geometric. RMSE and MAE were computed against ground-truth sensor readings.",
        "results": "GCN+GRU achieved RMSE of 3.81 km/h vs. LSTM baseline of 4.49 km/h (15.2% improvement) and a plain GCN of 4.12 km/h. MAE improved from 3.21 to 2.74 km/h. The model captured bottleneck propagation effects that LSTM missed. Prediction accuracy degraded slightly during typhoon events (RMSE +0.61 km/h).",
        "discussion": "Capturing spatial road dependencies via GCN substantially improves traffic flow prediction. The improvement is most pronounced at network junction nodes where upstream flow strongly impacts downstream speed. Typhoon-period degradation suggests the model would benefit from weather covariate features. Future work should test real-time inference at 5-minute intervals.",
    },
    {
        "title": "RFID-Based Inventory Management System for a Retail Store",
        "authors": "ESPINOSA, CARLA D. | MAGPAYO, ARNEL V.",
        "year": "2023", "dept": "Department of Computer Engineering", "degree": "BSCpE",
        "keywords": "RFID, inventory management, retail, embedded system, Arduino",
        "abstract": "This study implements an RFID-based inventory management system for a small retail store, reducing stockout incidents by 65% and inventory counting time by 80% through automated real-time tracking.",
        "introduction": "Small retail stores in the Philippines commonly rely on manual inventory count, resulting in stockouts, overstocking, and count errors. RFID technology enables automated real-time item tracking without line-of-sight scanning. This study designs and deploys an RFID inventory system for a grocery store in Imus City with approximately 1,200 SKUs.",
        "methods": "RFID tags (MIFARE Classic 1K) were attached to product units. Two RFID readers (RC522 modules) were installed at entry and exit gates, connected to Arduino Mega 2560. A web dashboard built in Flask tracked inventory counts in real time with PostgreSQL storage. Threshold alerts were configured per SKU (reorder point = safety stock + average daily demand × lead time). The system was deployed and monitored over 90 days.",
        "results": "Stockout incidents decreased from 23 per month to 8 per month (65% reduction). Inventory counting time decreased from 4.5 hours to 53 minutes (80% reduction). Inventory accuracy improved from 91.2% to 98.7%. Reader accuracy was 99.4% at a maximum read distance of 8cm. System uptime was 98.9% over the 90-day evaluation.",
        "discussion": "RFID automation delivers substantial operational improvements for small retail environments. The 1.3% remaining inventory inaccuracy stems from RFID tag detachment incidents. The reorder alert system effectively prevented critical stockouts. Future work should evaluate UHF RFID for longer read ranges and test scalability with 5,000+ SKU stores.",
    },
    {
        "title": "Sign Language Recognition System Using Mediapipe and LSTM",
        "authors": "AGUILAR, NINA S. | PASCUA, JEROME B.",
        "year": "2024", "dept": "Department of Computer Science", "degree": "BSCS",
        "keywords": "sign language recognition, Mediapipe, LSTM, accessibility, Filipino Sign Language",
        "abstract": "This study develops a Filipino Sign Language (FSL) recognition system using Mediapipe hand landmark extraction and an LSTM classifier, achieving 94.5% accuracy on a 30-word FSL vocabulary.",
        "introduction": "Deaf and hard-of-hearing individuals in the Philippines face communication barriers in educational and medical settings due to the shortage of FSL interpreters. Automated sign language recognition can bridge this gap. This study builds an FSL recognition system for the 30 most common conversation words, targeting real-time use on consumer laptop webcams.",
        "methods": "Mediapipe Hands was used to extract 21 3D hand landmark coordinates per frame (63 features). Sequences of 30 frames were collected for each of 30 FSL signs, with 60 sequences per sign (total 1,800 sequences from 10 signers). An LSTM network (2 layers, 64 units each) was trained on keypoint sequences with dropout=0.3. Evaluation: per-class F1-score, confusion matrix, and 5-fold cross-validation.",
        "results": "The LSTM achieved 94.5% accuracy on the test set. Per-class F1 ranged from 89% (THANK YOU, similar motion to SORRY) to 100% (simple static signs). Recognition latency averaged 0.11 seconds per sign. The system performed consistently across 8 of 10 signers; 2 left-handed signers showed 6% accuracy drop without mirroring augmentation.",
        "discussion": "Mediapipe's lightweight landmark extraction enables real-time FSL recognition on CPU-only devices. The left-handed signer gap was fixed post-evaluation by adding horizontal flip augmentation. Expanding the vocabulary to 100+ words is the primary next step, alongside integrating sentence-level context using a language model for more natural interpretation.",
    },
    {
        "title": "Automated Timetable Scheduling Using Genetic Algorithm",
        "authors": "MACARAEG, PAULO R. | LAZARO, VENUS T.",
        "year": "2023", "dept": "Department of Information Technology", "degree": "BSIT",
        "keywords": "genetic algorithm, timetable scheduling, constraint satisfaction, optimization",
        "abstract": "This study implements a Genetic Algorithm (GA) for automated academic timetable scheduling at CvSU Imus Campus, generating conflict-free schedules 87% faster than the manual process while satisfying all hard constraints.",
        "introduction": "University timetable scheduling is an NP-hard combinatorial optimization problem. Manual scheduling at CvSU Imus takes 3-4 weeks per semester and frequently results in conflicts requiring manual correction. This study applies a Genetic Algorithm to automate timetable generation for 32 curriculum programs, 180 faculty members, and 45 classrooms.",
        "methods": "The GA was implemented in Python with the following configuration: population size=100, generations=500, crossover rate=0.85, mutation rate=0.05, tournament selection. Chromosome encoding: each gene represents a (subject, faculty, room, timeslot) tuple. Fitness function penalizes: faculty conflicts (×100), room conflicts (×100), and soft constraints including faculty preference violations (×5). Hard constraints were always enforced.",
        "results": "The GA produced conflict-free schedules in 100% of 20 runs. Average computation time was 4.2 minutes vs. 3-4 weeks manually (87% time reduction). Soft constraint violations averaged 3.2 per schedule, compared to 8.1 in manually-generated schedules. Faculty preference satisfaction rate was 91.3%.",
        "discussion": "The GA reliably satisfies all hard scheduling constraints while significantly outperforming manual scheduling in time. The remaining soft constraint violations (primarily room capacity near-misses) are acceptable in practice. Future work should implement multi-objective optimization to explicitly balance faculty load distribution and student travel time between rooms.",
    },
    {
        "title": "Blockchain-Based Academic Credential Verification System",
        "authors": "ALCANTARA, JAN P. | MORALEDA, RUTH A.",
        "year": "2024", "dept": "Department of Information Systems", "degree": "BSIS",
        "keywords": "blockchain, credential verification, Ethereum, smart contract, academic records",
        "abstract": "This study implements a blockchain-based academic credential verification system on Ethereum using Solidity smart contracts, enabling tamper-proof diploma verification in under 3 seconds with zero credential fraud risk.",
        "introduction": "Diploma fraud and certificate forgery are significant problems in Philippine employment. Traditional credential verification requires contacting issuing institutions, which is slow and unreliable for foreign employers. Blockchain's immutability and decentralized verification offer a reliable solution. This study implements a credential management and verification system for CvSU using Ethereum's Sepolia testnet.",
        "methods": "Smart contracts were written in Solidity (v0.8.20) and deployed on Ethereum's Sepolia testnet. The system stores credential hashes (SHA-256 of student records) on-chain; full records are stored off-chain in IPFS. A React.js frontend integrates with MetaMask for institution admin authentication. Verification by employers uses a QR code linked to the on-chain hash. Gas costs and verification time were measured across 50 transactions.",
        "results": "Credential issuance took an average of 2.8 seconds on the Sepolia testnet. Verification by employers took 1.4 seconds. Zero false verifications occurred in 200 test cases including tampered credentials. Average transaction gas cost was 42,000 gwei (~$0.004 at testnet rates). The IPFS retrieval latency was 0.9 seconds.",
        "discussion": "Blockchain-based verification eliminates the trust dependency on centralized credential databases. The main scalability concern is Ethereum mainnet gas costs, which would be ≈$0.30/credential issuance. Future deployment should evaluate Layer 2 solutions (Polygon, Optimism) for cost reduction. Integration with the Civil Service Commission's verification portal would maximize adoption.",
    },
    {
        "title": "Skin Disease Classification Using Transfer Learning on Dermoscopy Images",
        "authors": "SORIANO, ELENA F. | CABRERA, MARK R.",
        "year": "2023", "dept": "Department of Computer Science", "degree": "BSCS",
        "keywords": "transfer learning, skin disease, dermoscopy, EfficientNet, medical imaging",
        "abstract": "This study applies EfficientNet-B3 transfer learning for 7-class skin disease classification on the ISIC 2019 dataset, achieving 89.1% accuracy and 0.91 AUC-ROC, matching dermatologist-level performance on common conditions.",
        "introduction": "Skin cancer is the most common cancer globally, and early diagnosis significantly improves survival rates. Dermatologist shortages in rural Philippine provinces make early detection challenging. Computer-aided diagnosis using deep learning on dermoscopy images can extend diagnostic coverage. This study fine-tunes EfficientNet-B3 on the ISIC 2019 benchmark dataset for 7-class skin lesion classification.",
        "methods": "EfficientNet-B3 pretrained on ImageNet was fine-tuned on ISIC 2019 (25,331 dermoscopy images, 7 classes). Class imbalance addressed by weighted cross-entropy + oversampling of minority classes. Training: 30 epochs, cosine LR schedule (initial LR=1e-4), batch size 32, image size 300×300. Train/val/test: 70/15/15 stratified split. Augmentation: elastic distortion, cutout, color jitter. Evaluation: accuracy, per-class AUC, confusion matrix.",
        "results": "EfficientNet-B3 achieved 89.1% accuracy and mean AUC-ROC of 0.91 on the test set. Melanoma class AUC was 0.93. Dermatofibroma class showed lowest performance (AUC 0.85) due to visual similarity to nevi. Number of parameters: 12M. Inference time: 18ms per image on NVIDIA RTX 3060.",
        "discussion": "EfficientNet-B3 delivers clinically relevant performance for automated skin lesion classification. The 0.93 melanoma AUC is comparable to published dermatologist performance (0.91-0.94). The model's confidence calibration is slightly overconfident on minority classes. Future work should validate on a locally-collected Filipino skin lesion dataset to address skin tone distribution differences.",
    },
    {
        "title": "Chatbot for University Inquiries Using Rasa NLU",
        "authors": "PADILLA, LIZA C. | TRINIDAD, ERNEST A.",
        "year": "2024", "dept": "Department of Information Technology", "degree": "BSIT",
        "keywords": "chatbot, Rasa NLU, intent classification, university information, conversational AI",
        "abstract": "This study develops a university inquiry chatbot for CvSU Imus Campus using Rasa NLU, achieving 93.8% intent classification accuracy across 28 intent categories for enrollment, fees, and schedule queries.",
        "introduction": "University registrar and administrative offices at CvSU Imus receive hundreds of repetitive inquiries daily regarding enrollment, tuition fees, class schedules, and academic calendar. A conversational AI chatbot can handle routine queries 24/7, reducing staff workload. This study builds and evaluates a domain-specific chatbot using Rasa's open-source NLU framework.",
        "methods": "Rasa NLU 3.0 was used with the DIETClassifier pipeline (transformer-based intent and entity extraction). The training dataset contains 1,840 annotated utterances across 28 intents collected from actual student inquiries. Responses are templated for factual queries and use Rasa forms for multi-turn enrollment workflows. The bot was deployed as a Facebook Messenger integration. Evaluation: intent classification accuracy, entity F1, and user satisfaction survey.",
        "results": "The DIETClassifier achieved 93.8% intent classification accuracy on the held-out test set. Entity F1 (for dates, program names, subject codes) was 91.2%. In a 2-week live pilot, the bot handled 1,247 conversations with a 79% resolution rate (without human handoff). Average user satisfaction was 4.1/5. The most common failure mode was out-of-scope queries (14.3% of sessions).",
        "discussion": "Rasa NLU provides a practical and customizable framework for domain-specific university chatbots. The 79% resolution rate is comparable to similar academic chatbot implementations. Out-of-scope handling requires a more robust fallback strategy; adding a catch-all GPT-based response generator is a recommended future enhancement. Full integration with CvSU's SIS for real-time enrollment data remains the highest-priority improvement.",
    },
    {
        "title": "Pneumonia Detection from Chest X-Rays Using VGG16",
        "authors": "ENRIQUEZ, JASPER O. | BELLO, CARLA M.",
        "year": "2023", "dept": "Department of Computer Science", "degree": "BSCS",
        "keywords": "pneumonia detection, VGG16, chest X-ray, medical imaging, transfer learning",
        "abstract": "This study fine-tunes VGG16 on the Kaggle Chest X-Ray dataset for binary pneumonia classification, achieving 95.5% accuracy and 0.97 AUC-ROC, demonstrating potential for supporting radiologist workflows.",
        "introduction": "Pneumonia is a leading cause of hospitalization in the Philippines, yet radiologist availability in provincial hospitals is limited. Deep learning models can assist in chest X-ray interpretation, flagging pneumonia cases for priority review. This study fine-tunes VGG16 on a publicly available chest X-ray dataset and evaluates clinical viability.",
        "methods": "VGG16 pretrained on ImageNet was fine-tuned on the Kaggle Chest X-Ray Images (Pneumonia) dataset (5,856 images: 1,583 Normal, 4,273 Pneumonia). Class imbalance was addressed by class-weighted loss (weight ratio 2.7:1). Training: 25 epochs, SGD optimizer (lr=0.001, momentum=0.9), batch size 32, image size 224×224. Augmentation: random rotation, width/height shift, zoom, horizontal flip. Evaluation: accuracy, AUC-ROC, sensitivity, specificity.",
        "results": "VGG16 achieved 95.5% accuracy, AUC-ROC 0.97, sensitivity 97.4%, and specificity 91.3%. False negatives (missed pneumonia) numbered 11 in the test set (4 bacterial, 7 viral). Grad-CAM visualizations confirmed the model attended to clinically relevant consolidation regions. Inference time: 45ms per image.",
        "discussion": "VGG16 transfer learning effectively detects pneumonia with high sensitivity, prioritizing recall to minimize missed cases. The 91.3% specificity is acceptable for a screening tool where further human review follows flagging. Grad-CAM validation builds clinician trust. Future work should validate on Filipino patient chest X-rays and evaluate under PACS integration in a provincial hospital setting.",
    },
    {
        "title": "Human Activity Recognition Using Smartphone Accelerometer Data and CNN-LSTM",
        "authors": "NAVARRO, ROMEO V. | CAPISTRANO, IRISH L.",
        "year": "2024", "dept": "Department of Computer Engineering", "degree": "BSCpE",
        "keywords": "human activity recognition, accelerometer, CNN-LSTM, wearable sensor, deep learning",
        "abstract": "This study proposes a CNN-LSTM hybrid model for human activity recognition using smartphone accelerometer data, achieving 97.1% accuracy on the UCI HAR dataset and 92.6% on a locally collected dataset.",
        "introduction": "Human Activity Recognition (HAR) from wearable sensor data has applications in healthcare monitoring, elder care, and fitness tracking. Smartphones provide built-in accelerometers and gyroscopes, enabling unobtrusive monitoring without additional hardware. This study builds a CNN-LSTM model that combines CNN's spatial feature extraction with LSTM's temporal modeling for robust activity classification.",
        "methods": "The UCI HAR dataset (10,299 windows, 6 activities: Walking, Walking Upstairs, Walking Downstairs, Sitting, Standing, Laying) was used as the primary benchmark. A local dataset was collected from 20 CvSU students using their smartphones (Samsung and iPhone) in real-world conditions. Input: 128-timestep windows of 3-axis accelerometer and gyroscope signals (6 channels). Model: 2 Conv1D layers → MaxPool → 2 LSTM layers (128 units) → Dense. Training: 50 epochs, Adam, batch 64.",
        "results": "On UCI HAR: 97.1% accuracy. On the local dataset: 92.6% accuracy. The 4.5% performance gap is attributed to device heterogeneity (different sampling rates). Per-activity F1: Walking 99%, Sitting 96%, Laying 100%. Hardest class: Walking Downstairs vs. Walking (F1=94% and 95% respectively). Model size: 2.3MB, suitable for on-device inference.",
        "discussion": "The CNN-LSTM hybrid outperforms pure CNN (95.3%) and pure LSTM (96.1%) on UCI HAR by capturing both spatial signal patterns and temporal dynamics. Device heterogeneity is the most impactful real-world challenge. Future work should implement on-device inference using TensorFlow Lite, apply federated learning for privacy-preserving personalization, and expand the local dataset.",
    },
    {
        "title": "Water Quality Monitoring System Using IoT Sensors and Machine Learning",
        "authors": "DIMACULANGAN, FRANCO A. | LACAP, JENNY M.",
        "year": "2023", "dept": "Department of Computer Engineering", "degree": "BSCpE",
        "keywords": "water quality, IoT, turbidity sensor, pH sensor, SVM, real-time monitoring",
        "abstract": "This study develops an IoT-based water quality monitoring system with SVM classification for detecting potability, achieving 94.2% classification accuracy and enabling real-time alerts for unsafe water conditions.",
        "introduction": "Access to clean water is a persistent challenge in coastal Cavite communities. Manual water quality testing is infrequent and slow. IoT-based continuous monitoring with automated classification can provide real-time safety alerts. This study deploys a multi-sensor IoT system in Bacoor Bay's water supply outlet and trains an SVM classifier to predict water potability.",
        "methods": "Sensors deployed: pH sensor, turbidity sensor (TSD-10), dissolved oxygen (DO) sensor, and temperature probe, all connected to ESP32 microcontroller with ThingSpeak cloud logging. 6 months of 15-minute interval sensor data (17,280 readings) were collected. SVM with RBF kernel was trained on labeled samples (WHO potability standards as ground truth). Features: pH, turbidity (NTU), DO (mg/L), temperature (°C). Evaluation: 5-fold cross-validation accuracy, precision, recall.",
        "results": "SVM achieved 94.2% classification accuracy, precision 93.8%, recall 94.6%. Turbidity and pH were the most discriminative features (ANOVA F-test). The system correctly identified 3 contamination events during the monitoring period that were later confirmed by LGU testing. Alert response time (sensor reading to SMS notification) averaged 12 seconds.",
        "discussion": "The IoT-SVM combination provides actionable, real-time water safety monitoring feasible for deployment in coastal communities. SVM's lightweight inference (0.001s) is ideal for edge deployment on ESP32. pH sensor drift was observed at 3-month intervals, necessitating regular recalibration. Future work should evaluate neural network models and extend sensor array with E. coli detection modules.",
    },
    {
        "title": "Automated Resume Screening System Using NLP and Cosine Similarity",
        "authors": "BONDOC, PATRICIA A. | REYES, CARL J.",
        "year": "2024", "dept": "Department of Information Systems", "degree": "BSIS",
        "keywords": "resume screening, NLP, TF-IDF, cosine similarity, HR technology, job matching",
        "abstract": "This study builds an automated resume screening system using TF-IDF and cosine similarity for job-resume matching, achieving 84.7% matching accuracy and reducing HR screening time by 73% in a company pilot.",
        "introduction": "HR departments in Philippine companies face high applicant volumes, making manual resume screening time-intensive and inconsistent. Automated screening tools can rank candidates by relevance to job descriptions. This study develops a web-based screening system for a BPO company in Dasmariñas City with 200 average monthly applicants.",
        "methods": "TF-IDF vectorization was applied to both job descriptions (JD) and resumes after preprocessing: stopword removal, stemming (NLTK), and skills entity extraction using spaCy's NER model fine-tuned on a resume corpus. Cosine similarity computed between JD and resume vectors produces a match score. A threshold of 0.45 was used to classify candidates as Shortlisted or Not Shortlisted. Pilot: 3 job openings, 120 applicants, evaluated against HR manager decisions.",
        "results": "The system achieved 84.7% accuracy against HR manager ground-truth decisions, precision 82.1%, recall 87.3%. Screening time was reduced from 3.5 minutes to 0.6 minutes per resume (73% reduction). Top candidates identified by the system produced 78% offer acceptance rate vs. 65% historical baseline. Skills NER extraction accuracy was 91.6%.",
        "discussion": "TF-IDF cosine similarity provides a strong, interpretable baseline for job-resume matching. The 84.7% accuracy ceiling is partly explained by subjective HR preferences not fully captured in textual matching (e.g., cultural fit). Future work should extend to BERT-based semantic matching and incorporate structured resume parsing for education and experience extraction.",
    },
    {
        "title": "Power Consumption Forecasting Using Prophet and ARIMA Models",
        "authors": "GASPAR, JOEL C. | AUSTRIA, MARIA T.",
        "year": "2023", "dept": "Department of Information Technology", "degree": "BSIT",
        "keywords": "power consumption, time series, Prophet, ARIMA, energy forecasting",
        "abstract": "This study compares Facebook Prophet and ARIMA for 30-day power consumption forecasting at CvSU Imus Campus, finding Prophet outperforms ARIMA with MAPE of 4.2% vs. 7.8%, especially for seasonal patterns.",
        "introduction": "Accurate power consumption forecasting enables universities to negotiate better electricity tariffs, plan load shedding, and improve energy efficiency. CvSU Imus pays approximately PHP 2.8M annually in electricity. A 5% prediction accuracy improvement could translate to PHP 140,000 in cost avoidance. This study compares classical (ARIMA) and modern (Prophet) time series models for campus power forecasting.",
        "methods": "Daily electricity consumption data (kWh) for CvSU Imus Campus from January 2020 to December 2022 (1,096 data points) was obtained from the campus facilities office. Data preprocessing: interpolation of 17 missing values, outlier capping at 3σ. ARIMA(2,1,2) was selected via AIC minimization. Prophet was configured with yearly and weekly seasonality, Philippine holidays as regressors, and COVID-19 lockdown period as a special event regressor. Walk-forward validation: monthly 30-day forecasts over 2022.",
        "results": "Prophet achieved MAPE of 4.2% vs ARIMA's 7.8% on the 2022 validation period. RMSE: Prophet 182 kWh vs ARIMA 341 kWh. Prophet outperformed most during semester start weeks (+82% accuracy lift), which correspond to high seasonality events. Both models underperformed during typhoon-induced power outages.",
        "discussion": "Prophet's superior handling of multi-seasonality and holiday regressors makes it better suited for academic institution energy forecasting where class calendars strongly drive consumption. ARIMA remains competitive during stable mid-semester periods. Future work should incorporate weather features (temperature, solar irradiance) and test LSTM-based models for further accuracy gains.",
    },
    {
        "title": "E-Learning Platform with Adaptive Quiz Generation Using Item Response Theory",
        "authors": "EVANGELISTA, SARAH M. | IGNACIO, JOHN P.",
        "year": "2024", "dept": "Department of Information Systems", "degree": "BSIS",
        "keywords": "e-learning, adaptive testing, Item Response Theory, IRT, quiz generation",
        "abstract": "This study develops an adaptive e-learning platform that uses Item Response Theory (IRT) to personalize quiz difficulty based on estimated student ability, improving learning outcomes by 18% over fixed-difficulty quizzes.",
        "introduction": "Standardized quizzes in e-learning systems fail to adapt to individual student ability levels, leading to frustration for struggling learners and boredom for advanced ones. Item Response Theory (IRT) provides a psychometric framework for dynamic difficulty adjustment. This study implements a 2-parameter IRT model in a web-based e-learning platform for BSIT programming courses at CvSU.",
        "methods": "A bank of 300 multiple-choice questions for 5 programming topics was calibrated using 2PL IRT (discrimination and difficulty parameters estimated via maximum likelihood). The adaptive algorithm uses Expected A Posteriori (EAP) ability estimation and selects the next item to maximize Fisher information. The system was built in Django with a Vue.js frontend. A quasi-experimental study compared adaptive (n=45) vs. fixed-quiz (n=45) groups over one semester. Pre-test and post-test scores measured learning gain.",
        "results": "The adaptive group showed 18.3% higher normalized learning gain than the fixed-quiz group (p<0.01, Cohen's d=0.72). Average quiz completion time was 12.4 minutes (adaptive) vs. 17.8 minutes (fixed), a 30% reduction. Student satisfaction was 4.3/5 (adaptive) vs. 3.7/5 (fixed). Item exposure rate was more balanced in adaptive testing (reduced overexposure of easy items by 41%).",
        "discussion": "IRT-based adaptive testing meaningfully improves learning efficiency and satisfaction compared to fixed quizzes. The statistically significant effect size (d=0.72) indicates practical pedagogical value. The primary implementation challenge was expert calibration of initial IRT parameters. Future work should automate parameter estimation via online EM as more student responses accumulate.",
    },
]


def build_pdf(paper, output_path):
    doc = SimpleDocTemplate(output_path, pagesize=LETTER,
                            rightMargin=inch, leftMargin=inch,
                            topMargin=inch, bottomMargin=inch)
    styles = getSampleStyleSheet()
    title_style   = ParagraphStyle('TitleS', parent=styles['Title'], fontSize=16, spaceAfter=6)
    heading_style = ParagraphStyle('HeadS',  parent=styles['Heading1'], fontSize=13, spaceBefore=14, spaceAfter=6)
    body_style    = ParagraphStyle('BodyS',  parent=styles['Normal'], fontSize=11, leading=16, alignment=TA_JUSTIFY)
    center_style  = ParagraphStyle('CentS',  parent=styles['Normal'], fontSize=11, alignment=TA_CENTER)

    story = []

    # Cover Page
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph(paper["title"].upper(), title_style))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph(f"Authors: {paper['authors']}", center_style))
    story.append(Paragraph(f"Year: {paper['year']}", center_style))
    story.append(Paragraph(paper["dept"], center_style))
    story.append(Paragraph(f"Degree Program: {paper['degree']}", center_style))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(f"<b>Keywords:</b> {paper['keywords']}", body_style))
    story.append(PageBreak())

    # Abstract
    story.append(Paragraph("ABSTRACT", heading_style))
    story.append(Paragraph(paper["abstract"], body_style))
    story.append(Spacer(1, 0.2 * inch))

    # INTRODUCTION
    story.append(Paragraph("INTRODUCTION", heading_style))
    story.append(Paragraph(paper["introduction"], body_style))
    story.append(Spacer(1, 0.2 * inch))

    # METHODOLOGY
    story.append(Paragraph("METHODOLOGY", heading_style))
    story.append(Paragraph(paper["methods"], body_style))
    story.append(Spacer(1, 0.2 * inch))

    # RESULTS
    story.append(Paragraph("RESULTS", heading_style))
    story.append(Paragraph(paper["results"], body_style))
    story.append(Spacer(1, 0.2 * inch))

    # DISCUSSION
    story.append(Paragraph("DISCUSSION", heading_style))
    story.append(Paragraph(paper["discussion"], body_style))

    doc.build(story)


def main():
    print(f"\nGenerating {len(PAPERS)} dummy IMRAD PDFs → {OUTPUT_DIR}\n")
    for i, paper in enumerate(PAPERS, 1):
        safe_title = paper["title"][:60].replace(" ", "_").replace("/", "-")
        filename = f"{i:02d}_{safe_title}.pdf"
        path = os.path.join(OUTPUT_DIR, filename)
        try:
            build_pdf(paper, path)
            print(f"  [{i:02d}] ✅ {filename}")
        except Exception as e:
            print(f"  [{i:02d}] ❌ {filename}: {e}")

    print(f"\nDone! {len(PAPERS)} PDFs saved in: {OUTPUT_DIR}\n")


if __name__ == "__main__":
    main()
