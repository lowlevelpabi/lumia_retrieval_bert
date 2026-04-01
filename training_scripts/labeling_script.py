import os
import csv

# A highly realistic mix of clean headings, messy OCR, and body text
labeled_data = [
    # --- INTRODUCTION HEADINGS ---
    ("CHAPTER 1: INTRODUCTION", "heading_intro"),
    ("I. INTRODUCTION", "heading_intro"),
    ("1. INTRODUCTION", "heading_intro"),
    ("Background of the Study", "heading_intro"),
    ("Statement of the Problem", "heading_intro"),
    ("Objectives of the Study", "heading_intro"),
    ("Significance of the Study", "heading_intro"),
    ("Scope and Delimitation", "heading_intro"),
    ("CHAPTER I", "heading_intro"),
    ("INTRODUCTION AND BACKGROUND", "heading_intro"),
    
    # --- METHODOLOGY HEADINGS ---
    ("CHAPTER 3: METHODOLOGY", "heading_methods"),
    ("CHAPTER III", "heading_methods"),
    ("RESEARCH METHODOLOGY", "heading_methods"),
    ("Research Design", "heading_methods"),
    ("Participants of the Study", "heading_methods"),
    ("Data Gathering Procedure", "heading_methods"),
    ("Statistical Treatment of Data", "heading_methods"),
    ("M E T H O D O L O G Y", "heading_methods"), # Simulating pypdf spacing
    ("System Development Methodology", "heading_methods"),
    
    # --- RESULTS HEADINGS ---
    ("CHAPTER 4: RESULTS AND DISCUSSION", "heading_results"),
    ("CHAPTER IV", "heading_results"),
    ("RESULTS AND DISCUSSIONS", "heading_results"),
    ("PRESENTATION, ANALYSIS AND INTERPRETATION OF DATA", "heading_results"),
    ("4. RESULTS", "heading_results"),
    ("System Testing Results", "heading_results"),
    ("Software Evaluation Results", "heading_results"),
    ("R E S U L T S", "heading_results"),
    
    # --- DISCUSSION/CONCLUSION HEADINGS ---
    ("CHAPTER 5: SUMMARY, CONCLUSIONS AND RECOMMENDATIONS", "heading_discussion"),
    ("CHAPTER V", "heading_discussion"),
    ("CONCLUSIONS AND RECOMMENDATIONS", "heading_discussion"),
    ("Summary of Findings", "heading_discussion"),
    ("5. Conclusion", "heading_discussion"),
    ("Implications and Recommendations", "heading_discussion"),
    
    # --- OTHER HEADINGS (Crucial to prevent false positives) ---
    ("CHAPTER 2: REVIEW OF RELATED LITERATURE", "heading_other"),
    ("REVIEW OF RELATED LITERATURE AND STUDIES", "heading_other"),
    ("Conceptual Framework", "heading_other"),
    ("Theoretical Framework", "heading_other"),
    ("ABSTRACT", "heading_other"),
    ("ACKNOWLEDGEMENT", "heading_other"),
    ("TABLE OF CONTENTS", "heading_other"),
    ("LIST OF FIGURES", "heading_other"),
    ("REFERENCES", "heading_other"),
    ("BIBLIOGRAPHY", "heading_other"),
    ("APPENDICES", "heading_other"),
    
    # --- BODY TEXT (The model must learn what a paragraph looks like) ---
    ("The main objective of this archiving system is to utilize BERT NLP for semantic search.", "body_text"),
    ("This study utilizes a descriptive quantitative research design to gather necessary data.", "body_text"),
    ("A total of 50 respondents from the Department of Computer Science evaluated the system.", "body_text"),
    ("Table 4 shows that the system achieved an overall weighted mean of 4.54, interpreted as Excellent.", "body_text"),
    ("Based on the findings, the researchers conclude that the machine learning approach is viable.", "body_text"),
    ("The Vue.js frontend communicates with the FastAPI backend via RESTful endpoints.", "body_text"),
    ("DistilBERT was fine-tuned to classify text chunks into their respective IMRAD sections.", "body_text"),
    ("Therefore, it is recommended to expand the dataset to include varying formats.", "body_text"),
    ("The researchers utilized Tesseract OCR to extract text from scanned PDF documents.", "body_text"),
    ("During the testing phase, several bugs were encountered and subsequently resolved.", "body_text"),
    ("As seen in Figure 2, the system architecture consists of three main modules.", "body_text"),
    ("The proponents recommend that future researchers implement a cloud-based database.", "body_text"),
    ("This chapter presents the data gathered, alongside its corresponding analysis.", "body_text"),
    ("In partial fulfillment of the requirements for the degree of Bachelor of Science in Information Technology.", "body_text"),
    
    # --- JUNK / OCR ERRORS / BOILERPLATE ---
    ("14", "junk"),
    ("iv", "junk"),
    ("Cavite State University", "junk"),
    ("CvSU", "junk"),
    ("Imus Campus", "junk"),
    ("Table 1.1", "junk"),
    ("Figure 4. System Flowchart", "junk"),
    ("METH0D0L0GY", "junk"), # OCR error
    ("............", "junk"), # TOC dots
    ("Contribution No.", "junk"),
    ("Adviser:", "junk"),
    ("Department of Computer Science", "junk"),
    ("2026", "junk"),
]

OUTPUT_FOLDER = "./training_csv"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Write to CSV
file_name = "imrad_ds2002.csv"
output_path = os.path.join(OUTPUT_FOLDER, "lumia_trainext_" + file_name)

with open(output_path, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["text", "label"]) # Header required by Colab script
    writer.writerows(labeled_data)

print(f"Successfully generated '{output_path}' with {len(labeled_data)} labeled examples!")
print("You can upload this directly to Google Colab now. Please copy and paste the training code in colab_train.imrad.py")