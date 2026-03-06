"""
Test script for IMRAD section detection.
Run from the project root with: python scripts/test_imrad.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.imrad_service import imrad_service

# ─────────────────────────────────────────────────────────────────────────────
# Test fixtures — simulate different thesis heading styles
# ─────────────────────────────────────────────────────────────────────────────

IMRAD_STYLE_TEXT = """
TITLE: Automated Plant Disease Detection Using Convolutional Neural Networks

AUTHORS: DELA CRUZ, MARIA S. | REYES, JUAN A.

ABSTRACT
This study presents a CNN-based system for detecting plant diseases from leaf images.
A dataset of 5,000 annotated images was used for training and evaluation.

INTRODUCTION
Agriculture is a critical sector in the Philippine economy. Early detection of plant diseases
can prevent significant yield losses. This study addresses the gap by proposing an automated
detection system using deep learning. The objectives are: (1) to develop a CNN model for
multi-class leaf disease classification; (2) to evaluate its accuracy on a real-world dataset.

METHODOLOGY
This study employed Convolutional Neural Networks (CNN) using the ResNet-50 architecture.
The dataset consists of 5,000 leaf images from the PlantVillage dataset, categorized into
10 disease classes. The dataset was split 80/20 for training and validation. Data augmentation
techniques were applied including horizontal flip, rotation (±15°), and brightness adjustment.
The model was trained for 50 epochs using Adam optimizer with a learning rate of 0.001.
A confusion matrix and classification report were used to evaluate model performance.

RESULTS
The proposed CNN model achieved an overall accuracy of 93.4% on the validation dataset.
Precision was 92.1%, recall was 93.8%, and F1-score was 92.9%. The model performed best
on Powdery Mildew (97%) and struggled most with Early Blight vs Late Blight distinction (87%).
Training time was approximately 4.5 hours on an NVIDIA GTX 1060 GPU.

DISCUSSION
The results confirm that CNNs are effective for plant disease classification. The 93.4% accuracy
surpasses the previous baseline of 87% from SVM-based classifiers. Misclassification between
Early Blight and Late Blight is attributed to visual similarity and low inter-class variance.
Future work should explore Vision Transformers and larger domain-specific datasets.
"""

CHAPTER_STYLE_TEXT = """
TITLE: Smart Attendance System Using Facial Recognition

AUTHOR: SANTOS, JOSE B.

ABSTRACT
This study proposes a smart attendance system using facial recognition powered by FaceNet.

CHAPTER I
Attendance monitoring is a labor-intensive task in higher education. Manual entry is prone to
errors and proxy attendance. This study proposes an automated face recognition system using
FaceNet embeddings and SVM classification for real-time attendance logging. Objectives include:
(1) designing the facial recognition pipeline; (2) integrating with a web dashboard.

CHAPTER II
The research design is experimental. FaceNet (Inception ResNet V1) was used to generate
128-dimensional face embeddings. An SVM classifier with an RBF kernel was trained on a dataset
of 200 students (10 images per student). The system was deployed on a Raspberry Pi 4.
Evaluation metrics include accuracy, false acceptance rate (FAR), and false rejection rate (FRR).

CHAPTER IV
The system achieved 96.2% recognition accuracy under controlled lighting conditions. FAR was
0.3% and FRR was 3.5%. Processing time averaged 350ms per recognition event. Performance
degraded to 88% accuracy under low-light conditions, indicating a lighting dependency.

CHAPTER V
The proposed system demonstrates that FaceNet-based facial recognition is viable for automated
attendance. The 96.2% accuracy under controlled conditions meets practical deployment standards.
Low-light sensitivity remains a limitation. Future work should incorporate infrared cameras and
test in real classroom environments with varying student populations.
"""

NO_HEADINGS_TEXT = """
This paper discusses machine learning techniques for natural language processing tasks.
Various transformer-based models were evaluated on the GLUE benchmark.
Results show that BERT outperforms earlier baselines consistently.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Test runner
# ─────────────────────────────────────────────────────────────────────────────

def run_tests():
    passed = 0
    failed = 0

    def check(name, condition, detail=""):
        nonlocal passed, failed
        if condition:
            print(f"  ✅ PASS: {name}")
            passed += 1
        else:
            print(f"  ❌ FAIL: {name} {detail}")
            failed += 1

    # ── Test 1: IMRAD-style headings ─────────────────────────────────────────
    print("\n[Test 1] IMRAD-style headings (INTRODUCTION, METHODOLOGY, RESULTS, DISCUSSION)")
    s1 = imrad_service.extract_sections(IMRAD_STYLE_TEXT)
    check("'introduction' detected",    "introduction" in s1)
    check("'methods' detected",         "methods" in s1)
    check("'results' detected",         "results" in s1)
    check("'discussion' detected",      "discussion" in s1)
    check("introduction contains 'objectives'",    "objectives" in s1.get("introduction", "").lower())
    check("methods contains 'resnet'",             "resnet" in s1.get("methods", "").lower())
    check("results contains 'accuracy'",           "accuracy" in s1.get("results", "").lower())
    check("discussion contains 'cnn'",             "cnn" in s1.get("discussion", "").lower())
    check("intro does NOT bleed into methods",     "resnet" not in s1.get("introduction", "").lower())

    # ── Test 2: CvSU Chapter-style headings ──────────────────────────────────
    print("\n[Test 2] CvSU Chapter-style headings (CHAPTER I, II, IV, V)")
    s2 = imrad_service.extract_sections(CHAPTER_STYLE_TEXT)
    check("'introduction' (CHAPTER I) detected",  "introduction" in s2)
    check("'methods' (CHAPTER II) detected",      "methods" in s2)
    check("'results' (CHAPTER IV) detected",      "results" in s2)
    check("'discussion' (CHAPTER V) detected",    "discussion" in s2)
    check("methods contains 'svm'",               "svm" in s2.get("methods", "").lower())
    check("results contains 'accuracy'",          "accuracy" in s2.get("results", "").lower())

    # ── Test 3: No headings text ──────────────────────────────────────────────
    print("\n[Test 3] Text with no IMRAD or chapter headings")
    s3 = imrad_service.extract_sections(NO_HEADINGS_TEXT)
    check("Returns empty dict (no false positives)", len(s3) == 0, f"got {list(s3.keys())}")

    # ── Test 4: get_all_vector_names ─────────────────────────────────────────
    print("\n[Test 4] get_all_vector_names()")
    from app.services.imrad_service import INCLUDE_ABSTRACT_VECTOR
    names = imrad_service.get_all_vector_names()
    check("'title' always present",            "title" in names)
    check("'introduction' present",            "introduction" in names)
    check("'methods' present",                 "methods" in names)
    check("'results' present",                 "results" in names)
    check("'discussion' present",              "discussion" in names)
    if INCLUDE_ABSTRACT_VECTOR:
        check("'abstract' present (flag=True)", "abstract" in names)
    else:
        check("'abstract' absent (flag=False)", "abstract" not in names)

    # ── Test 5: build_vectors (no actual embedding model needed for structure test)
    print("\n[Test 5] build_vectors() output structure")
    vectors = imrad_service.build_vectors(
        title="Test Title Paper",
        sections=s1,
        abstract="This is a short abstract."
    )
    check("'title' vector generated",         "title" in vectors)
    check("'introduction' vector generated",  "introduction" in vectors)
    check("'methods' vector generated",       "methods" in vectors)
    check("All vectors are lists of floats",
          all(isinstance(v, list) and len(v) == 384 for v in vectors.values()))

    # ── Summary ───────────────────────────────────────────────────────────────
    total = passed + failed
    print(f"\n{'='*55}")
    print(f"Results: {passed}/{total} passed | {failed} failed")
    print(f"{'='*55}\n")

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
