import os
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register Arial font with fallbacks
try:
    font_dir = "C:/Windows/Fonts"
    pdfmetrics.registerFont(TTFont('Arial', os.path.join(font_dir, "arial.ttf")))
    pdfmetrics.registerFont(TTFont('Arial-Bold', os.path.join(font_dir, "arialbd.ttf")))
    pdfmetrics.registerFont(TTFont('Arial-Italic', os.path.join(font_dir, "ariali.ttf")))
    font_name = 'Arial'
    font_bold = 'Arial-Bold'
    font_italic = 'Arial-Italic'
except Exception:
    font_name = 'Helvetica'
    font_bold = 'Helvetica-Bold'
    font_italic = 'Helvetica-Oblique'

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute total pages and add running headers/footers
    on all pages except the cover page. Optimized for A4 paper layout.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        # Page 1 is the cover page; do not draw headers/footers
        if self._pageNumber == 1:
            return
        
        self.saveState()
        
        # ─── HEADER ───
        # Margins: L: 1.5 in (108 pt), R: 1 in (72 pt). Width: A4 = 595.27 pt.
        # Header text starts at x=108 and ends at x=523.27 (595.27-72)
        # Top of A4 is 841.89 pt. Top Margin = 72 pt.
        self.setFont(font_bold, 8)
        self.setFillColor(colors.HexColor("#007F3E")) # Lumia Brand Green
        self.drawString(108, 801.89, "LUMIA — SMART RESEARCH")
        
        self.setFont(font_name, 8)
        self.setFillColor(colors.HexColor("#4A5568"))
        self.drawRightString(523.27, 801.89, "User & Technical Operation Manual")
        
        # Header Line
        self.setStrokeColor(colors.HexColor("#A3E635")) # Accent Lime Green
        self.setLineWidth(0.75)
        self.line(108, 793.89, 523.27, 793.89)
        
        # ─── FOOTER ───
        self.setFont(font_name, 8)
        self.setFillColor(colors.HexColor("#4A5568"))
        self.drawString(108, 42, "Department of Computer Studies | Academic Year 2025-2026")
        
        text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(523.27, 42, text)
        
        # Footer Line
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.5)
        self.line(108, 54, 523.27, 54)
        
        self.restoreState()

def build_pdf(filename="SMART_RESEARCH_User_Manual.pdf"):
    # Target dimensions: A4 page size = 595.27 x 841.89 pt
    # Printable area: Left Margin 1.5 in (108 pt), other margins 1 in (72 pt) -> printable width = 415.27 pt
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        leftMargin=108,
        rightMargin=72,
        topMargin=72,
        bottomMargin=72
    )

    styles = getSampleStyleSheet()
    
    # Resolve paths relative to backend directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(script_dir)
    logo_path = os.path.join(backend_dir, "lumia_logo.png")
    search_path = os.path.join(backend_dir, "search_screenshot.jpg")
    upload_path = os.path.join(backend_dir, "upload_screenshot.jpg")

    # ─── CUSTOM BRANDED STYLES ───
    brand_primary = colors.HexColor("#007F3E")   # Rich Lumia Brand Green
    brand_secondary = colors.HexColor("#1A202C") # Off-Black / Dark Charcoal
    brand_accent = colors.HexColor("#E8F5E9")    # Soft background light green
    text_color = colors.HexColor("#1A202C")      # Body Text
    light_text = colors.HexColor("#4A5568")      # Charcoal Grey

    title_style = ParagraphStyle(
        name='CoverTitle',
        fontName=font_bold,
        fontSize=20,
        leading=26,
        alignment=1, # Center
        textColor=brand_primary,
        spaceAfter=15
    )
    
    subtitle_style = ParagraphStyle(
        name='CoverSubtitle',
        fontName=font_name,
        fontSize=12,
        leading=16,
        alignment=1, # Center
        textColor=brand_secondary,
        spaceAfter=40
    )

    meta_style = ParagraphStyle(
        name='CoverMeta',
        fontName=font_name,
        fontSize=11,
        leading=14,
        alignment=1, # Center
        textColor=text_color,
        spaceAfter=11
    )
    
    author_header_style = ParagraphStyle(
        name='CoverAuthorHeader',
        fontName=font_bold,
        fontSize=11,
        leading=14,
        alignment=1,
        textColor=brand_primary,
        spaceAfter=11
    )

    h1_style = ParagraphStyle(
        name='Heading1_Custom',
        fontName=font_bold,
        fontSize=16,
        leading=20,
        textColor=brand_primary,
        spaceBefore=22,
        spaceAfter=22,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        name='Heading2_Custom',
        fontName=font_bold,
        fontSize=13,
        leading=17,
        textColor=brand_secondary,
        spaceBefore=22,
        spaceAfter=22,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        name='Body_Custom',
        fontName=font_name,
        fontSize=11,
        leading=14,
        textColor=text_color,
        alignment=4, # Justify
        spaceAfter=22 # Double Spacing between paragraphs
    )

    bullet_style = ParagraphStyle(
        name='Bullet_Custom',
        parent=body_style,
        fontName=font_name,
        fontSize=11,
        leading=14,
        leftIndent=20,
        firstLineIndent=-10,
        alignment=4, # Justify
        spaceAfter=22
    )

    table_header_style = ParagraphStyle(
        name='TableHeader',
        fontName=font_bold,
        fontSize=11,
        leading=14,
        textColor=colors.white
    )

    table_body_style = ParagraphStyle(
        name='TableBody',
        fontName=font_name,
        fontSize=11,
        leading=14,
        textColor=text_color
    )
    
    table_body_bold_style = ParagraphStyle(
        name='TableBodyBold',
        fontName=font_bold,
        fontSize=11,
        leading=14,
        textColor=text_color
    )

    callout_style = ParagraphStyle(
        name='CalloutText',
        fontName=font_italic,
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1C3D27")
    )

    story = []

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 1: COVER PAGE
    # ════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 20))
    
    # Decorative color bar at the top (width 415 pt matches A4 width)
    dec_bar = Table([[""]], colWidths=[415], rowHeights=[6])
    dec_bar.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), brand_primary),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(dec_bar)
    story.append(Spacer(1, 20))

    # Main Title
    title_text = "LUMIA: AN AI-POWERED WEB-BASED RESEARCH PAPER RETRIEVAL AND RECOMMENDATION SYSTEM"
    story.append(Paragraph(title_text, title_style))
    story.append(Spacer(1, 5))

    # Subtitle
    story.append(Paragraph("USER & TECHNICAL OPERATION MANUAL (Lumia Version 2.0)", subtitle_style))
    
    # Embed System Logo on Cover Page
    if os.path.exists(logo_path):
        logo_img = Image(logo_path, width=80, height=80)
        t_logo = Table([[logo_img]], colWidths=[415])
        t_logo.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 30),
            ('TOPPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(t_logo)
    else:
        story.append(Spacer(1, 30))
    
    # Metadata Block
    story.append(Paragraph("<b>ACADEMIC DEPARTMENT:</b>", author_header_style))
    story.append(Paragraph("Department of Computer Studies", meta_style))
    story.append(Spacer(1, 8))
    
    story.append(Paragraph("<b>ACADEMIC YEAR:</b>", author_header_style))
    story.append(Paragraph("2025-2026", meta_style))
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>PREPARED BY:</b>", author_header_style))
    proponents = "RYAN ANDREW A. REYES &bull; MARIA MANELUZ A. ORANG &bull; PRINCE ISIAH R. BILLONES"
    story.append(Paragraph(proponents, meta_style))
    
    story.append(Spacer(1, 30))
    
    # Decorative bottom footer text on cover page
    story.append(Paragraph("<font color='#A0AEC0'>System Operation & Technical Guide</font>", meta_style))
    
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 2: TABLE OF CONTENTS & INTRODUCTION
    # ════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Table of Contents", h1_style))
    story.append(Spacer(1, 8))
    
    # Width: 415. Col widths: 345, 70
    toc_data = [
        [Paragraph("<b>Document Section</b>", table_body_bold_style), Paragraph("<b>Page</b>", table_body_bold_style)],
        [Paragraph("Introduction", table_body_style), Paragraph("2", table_body_style)],
        [Paragraph("1. System Core Concept", table_body_style), Paragraph("3", table_body_style)],
        [Paragraph("2. User Privilege Matrix", table_body_style), Paragraph("3", table_body_style)],
        [Paragraph("3. Getting Started", table_body_style), Paragraph("4", table_body_style)],
        [Paragraph("4. Features & Functionality (Student Portal)", table_body_style), Paragraph("5", table_body_style)],
        [Paragraph("5. Features & Functionality (Faculty & Admin)", table_body_style), Paragraph("6", table_body_style)],
        [Paragraph("6. Installation & Deployment Guide (Prerequisites & Backend)", table_body_style), Paragraph("8", table_body_style)],
        [Paragraph("7. Installation & Deployment Guide (Frontend & Launch)", table_body_style), Paragraph("9", table_body_style)],
        [Paragraph("8. Installation & Deployment Guide (PostgreSQL & Maintenance)", table_body_style), Paragraph("10", table_body_style)],
        [Paragraph("9. Technical Troubleshooting Guide", table_body_style), Paragraph("11", table_body_style)],
        [Paragraph("10. Technical Support, Authors & Glossary", table_body_style), Paragraph("12", table_body_style)],
    ]
    
    t_toc = Table(toc_data, colWidths=[345, 70])
    t_toc.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEBELOW', (0,0), (-1,0), 1, brand_primary),
        ('LINEBELOW', (0,1), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_toc)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("Introduction", h1_style))
    intro_p1 = (
        "Welcome to the <b>Lumia User & Technical Operation Manual</b>. This manual provides "
        "comprehensive documentation for understanding, installing, operating, and maintaining the Lumia Research Retrieval System—an "
        "AI-powered, web-based capstone and thesis repository utilizing advanced <b>BERT-NLP semantic search</b> "
        "and IMRAD-aware structure extraction."
    )
    intro_p2 = (
        "This system replaces traditional keyword matching database lookups with deep natural language queries, allowing "
        "students, faculty, and researchers to locate academic documents based on contextual meaning rather than matching words. "
        "This document guides students through query techniques, faculty through document ingestion/OCR, admins through "
        "approvals, and IT staff through technical installations, environment configurations, and deployment procedures."
    )
    story.append(Paragraph(intro_p1, body_style))
    story.append(Paragraph(intro_p2, body_style))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 3: CORE CONCEPT & USER PRIVILEGE MATRIX
    # ════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("1. System Core Concept", h1_style))
    concept_txt_1 = (
        "<b>LUMIA</b> is an advanced, AI-powered web-based research paper repository designed to catalog "
        "and retrieve institutional capstones and undergraduate theses. Traditional search systems rely on database "
        "keyword matching, which limits searches to exact words. Lumia resolves this by employing semantic vector "
        "search using <b>BERT-NLP</b> (via the <b>Sentence-Transformers</b> model: <i>multi-qa-MiniLM-L6-cos-v1</i>)."
    )
    concept_txt_2 = (
        "Additionally, the system utilizes a unique <b>IMRAD-Aware Retrieval strategy</b>. When research PDFs are uploaded, "
        "the backend runs Optical Character Recognition (OCR) and splits the extracted text into structural sections: "
        "<b>Introduction, Methods, Results, and Discussion (IMRAD)</b>. These sections are embedded as independent "
        "high-dimensional vectors in a local or cloud <b>Qdrant Vector Database</b>. This enables users to perform targeted semantic searches, "
        "such as querying specifically for a methodology or statistical technique."
    )
    story.append(Paragraph(concept_txt_1, body_style))
    story.append(Paragraph(concept_txt_2, body_style))
    
    story.append(Paragraph("2. User Privilege Matrix", h1_style))
    story.append(Paragraph(
        "Access to the system features is guarded by a role-based authentication model. Users are mapped to "
        "specific groups depending on academic roles.", body_style
    ))
    story.append(Spacer(1, 8))

    # Privilege Matrix Table (Width: 415. Col widths: 145, 90, 90, 90)
    priv_data = [
        [
            Paragraph("System Capability", table_header_style),
            Paragraph("Student (User)", table_header_style),
            Paragraph("Faculty Member", table_header_style),
            Paragraph("Administrator", table_header_style)
        ],
        [
            Paragraph("<b>Search & Academic Filtering</b>", table_body_style),
            Paragraph("Yes", table_body_style),
            Paragraph("Yes", table_body_style),
            Paragraph("Yes", table_body_style)
        ],
        [
            Paragraph("<b>Read Metadata & Abstract</b>", table_body_style),
            Paragraph("Yes", table_body_style),
            Paragraph("Yes", table_body_style),
            Paragraph("Yes", table_body_style)
        ],
        [
            Paragraph("<b>Upload Research Documents</b>", table_body_style),
            Paragraph("Yes (Requires Approval)", table_body_style),
            Paragraph("Yes", table_body_style),
            Paragraph("Yes", table_body_style)
        ],
        [
            Paragraph("<b>Approve Pending Uploads</b>", table_body_style),
            Paragraph("No", table_body_style),
            Paragraph("No", table_body_style),
            Paragraph("Yes", table_body_style)
        ],
        [
            Paragraph("<b>User Accounts Moderation</b>", table_body_style),
            Paragraph("No", table_body_style),
            Paragraph("No", table_body_style),
            Paragraph("Yes", table_body_style)
        ],
        [
            Paragraph("<b>System Logs & Audit Control</b>", table_body_style),
            Paragraph("No", table_body_style),
            Paragraph("No", table_body_style),
            Paragraph("Yes", table_body_style)
        ]
    ]

    t_priv = Table(priv_data, colWidths=[145, 90, 90, 90])
    t_priv.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), brand_primary),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#F1F8F5"), colors.HexColor("#E8F5E9")]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_priv)
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 4: GETTING STARTED
    # ════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("3. Getting Started", h1_style))
    
    story.append(Paragraph("3.1 Registration & Authentication", h2_style))
    story.append(Paragraph(
        "Users access the system through a secure registration and login process. To create a student account, "
        "navigate to the <b>Register</b> portal (<code>reg_win.vue</code>), enter your full name, student email, preferred "
        "username, and password. Faculty and Administrator accounts are created directly by administrators or require "
        "role upgrading. Access to protected areas is gated by JWT tokens; attempts to access these pages without "
        "authenticating will redirect to the login module (<code>auth_win.vue</code>).", body_style
    ))
    
    story.append(Paragraph("3.2 Basic System Navigation", h2_style))
    story.append(Paragraph(
        "Lumia features a theme-aware interface supporting dark and light modes. Theme preference is automatically "
        "synced with user profiles. Key navigation components include the central search dashboard, the document upload "
        "wizard, and the admin control panel. The layout is optimized to adjust dynamically between mobile and desktop viewports, "
        "ensuring usability across multiple device profiles.", body_style
    ))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 5: FEATURES & FUNCTIONALITY (STUDENT PORTAL)
    # ════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("4. Features & Functionality", h1_style))
    
    story.append(Paragraph("4.1 Student Portal & Search Interface", h2_style))
    story.append(Paragraph(
        "The primary discovery mechanism is the <b>Explore Portal</b> (<code>explore_win.vue</code>), which provides "
        "hybrid search capabilities. Relational SQL matching executes concurrently with Qdrant vector search to compute "
        "overall cosine similarity scores. This ensures accurate retrieval based on contextual meaning.", body_style
    ))
    
    # Center and embed Search interface screenshot (Page 5)
    if os.path.exists(search_path):
        search_img = Image(search_path, width=380, height=214)
        t_search = Table([[search_img]], colWidths=[415])
        t_search.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(t_search)
    
    story.append(Paragraph("&bull; <b>Target Section Dropdown:</b> Focuses semantic query matching to specific structural paper sections such as Introduction, Methodology, Results, or Discussion.", bullet_style))
    story.append(Paragraph("&bull; <b>Academic Filter Controls:</b> Filters results by Department (BSCS, BSIT, BSCpE), Project Type (Capstone vs Thesis), or Publication Year ranges.", bullet_style))
    
    story.append(Paragraph("4.2 Document Detail View & Citations", h2_style))
    story.append(Paragraph(
        "Selecting a search result loads the <b>Paper Detail View</b> (<code>detail_win.vue</code>). This view shows "
        "extracted metadata, structured section contents, figures, and citation listings. The recommendation engine "
        "computes 'Narrow Down' recommendations by comparing the methods vector of the active document with overall index "
        "entries. Dynamic citation generators export reference strings in APA 6th, 7th, and in-text citation styles.", body_style
    ))
    
    story.append(Paragraph("4.3 Student Research Paper Submission", h2_style))
    story.append(Paragraph(
        "Students can submit their completed capstones and theses through the student upload portal (<code>up_win.vue</code>). "
        "Submissions are added as pending records and will not be vectorized or display in search indexes "
        "until an administrator reviews and approves the record.", body_style
    ))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 6 & 7: FEATURES & FUNCTIONALITY (FACULTY & ADMIN PORTALS)
    # ════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("4.4 Faculty Guided 3-Step Ingestion Flow", h2_style))
    story.append(Paragraph(
        "Faculty members ingest and index documents via a structured 3-step wizard in the upload portal:", body_style
    ))
    
    story.append(Paragraph("<b>Step 1: Document Upload & Ingestion Strategy Selection</b>", body_style))
    story.append(Paragraph(
        "The user uploads a PDF file and selects either <i>Smart Extract (OCR)</i> to auto-parse metadata and extract sections "
        "using PyTesseract, or <i>Manual Input</i> to input document details directly without OCR processing.", bullet_style
    ))
    
    story.append(Paragraph("<b>Step 2: Thumbnail Review & Page Indexing Selection</b>", body_style))
    story.append(Paragraph(
        "A grid of page thumbnails displays side-by-side with OCR-extracted text. Users click thumbnails to zoom and deselect "
        "non-academic pages (cover pages, signature forms, references) to prevent noise from contaminating vector databases.", bullet_style
    ))
    
    # Center and embed Ingestion portal screenshot (Page 6)
    if os.path.exists(upload_path):
        upload_img = Image(upload_path, width=380, height=214)
        t_upload = Table([[upload_img]], colWidths=[415])
        t_upload.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(t_upload)
        
    story.append(Paragraph("<b>Step 3: Metadata Auditing & Vector Indexing</b>", body_style))
    story.append(Paragraph(
        "The user reviews extracted metadata. Missing or incorrect fields are updated manually. Authors must be registered using "
        "the <code>|</code> pipe delimiter to format names correctly in individual entry boxes. Clicking <b>Submit and Index</b> "
        "saves metadata to SQL and indexes section vectors in Qdrant.", bullet_style
    ))

    # Note / Tip Box using single cell table (Width A4: 415)
    note_content = [
        [Paragraph("<b>💡 TIP: Page Selection Accuracy</b><br/>"
                   "Deselecting non-academic content pages (e.g., acknowledgement lists, reference sheets) in Step 2 directly "
                   "improves the semantic retrieval accuracy of the system, since only pure technical information will be vectorized.", callout_style)]
    ]
    t_note = Table(note_content, colWidths=[415])
    t_note.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F1F8F5")),
        ('BOX', (0,0), (-1,-1), 1, brand_primary),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(Spacer(1, 8))
    story.append(t_note)
    story.append(Spacer(1, 15))

    story.append(Paragraph("4.5 Administrator Management Console", h2_style))
    story.append(Paragraph(
        "Administrators access the <b>Management Deck</b> (<code>manage_win.vue</code>) to oversee platform operations. "
        "This includes viewing system dashboard analytics, managing user accounts, upgrading roles to Faculty or Admin, "
        "and approving or deleting pending student documents. The audit log screen monitors relational events (uploads, edits, deletions) "
        "recorded directly from the database.", body_style
    ))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 8: INSTALLATION GUIDE (PREREQUISITES & BACKEND ENV)
    # ════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("5. Installation & Deployment Guide", h1_style))
    story.append(Paragraph(
        "This section describes system deployment procedures, prerequisite packages, environment variables, "
        "and operational commands for running the Lumia platform.", body_style
    ))
    
    story.append(Paragraph("5.1 System Requirements & Prerequisites", h2_style))
    story.append(Paragraph(
        "Before setting up the repositories, install the following external system-level binaries:", body_style
    ))
    story.append(Paragraph("1. <b>Tesseract OCR:</b> Install UB-Mannheim Tesseract OCR installer. Add the installation folder to the system's Environment <code>PATH</code> variable.", bullet_style))
    story.append(Paragraph("2. <b>Poppler Library:</b> Extract Poppler Windows binaries. Add the <code>/bin</code> subdirectory to the system's Environment <code>PATH</code> variable to enable PDF rendering.", bullet_style))
    story.append(Paragraph("3. <b>Node.js:</b> Install LTS version 20.0 or higher.", bullet_style))
    story.append(Paragraph("4. <b>Python:</b> Install Python version 3.10 or higher.", bullet_style))
    story.append(Paragraph("5. <b>Docker:</b> Install Docker Desktop to run a production-ready instance of Qdrant Vector Database.", bullet_style))
    
    story.append(Paragraph("5.2 Vector Database Setup", h2_style))
    story.append(Paragraph(
        "Qdrant stores the 6-vector IMRAD schema. For local testing, it runs in file-storage mode. For production, run the Docker image:", body_style
    ))
    
    # Code snippet block (width 415)
    code_content = [[
        Paragraph("<font face='Courier' color='#FFFFFF' size='8'>"
                  "docker run -d -p 6333:6333 -p 6334:6334 \\<br/>"
                  "&nbsp;&nbsp;-v qdrant_storage:/qdrant/storage \\<br/>"
                  "&nbsp;&nbsp;qdrant/qdrant"
                  "</font>", table_body_bold_style)
    ]]
    t_code = Table(code_content, colWidths=[415])
    t_code.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#2D3748")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#1A202C")),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_code)
    story.append(Spacer(1, 8))

    story.append(Paragraph("5.3 Backend Environment Configuration (FastAPI)", h2_style))
    story.append(Paragraph(
        "Create a <code>.env</code> file in the backend root directory <code>lumia_retrieval_bert</code>:", body_style
    ))
    
    env_content = [[
        Paragraph("<font face='Courier' color='#FFFFFF' size='8'>"
                  "# Relational database (Default SQLite for dev, PostgreSQL for production)<br/>"
                  "DATABASE_URL=sqlite:///./thesis.db<br/>"
                  "# Vector database configuration<br/>"
                  "QDRANT_URL=http://localhost:6333<br/>"
                  "# Toggle Sample Document Ingestion<br/>"
                  "ENABLE_SAMPLE_DOCS=false"
                  "</font>", table_body_bold_style)
    ]]
    t_env = Table(env_content, colWidths=[415])
    t_env.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#2D3748")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#1A202C")),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_env)
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 9: INSTALLATION GUIDE (FRONTEND CONFIG & SERVICE LAUNCH)
    # ════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("5.4 Frontend Environment Configuration (Vue 3)", h2_style))
    story.append(Paragraph(
        "Create a <code>.env</code> file in the frontend root directory <code>lumia_frontend_sample</code> to link with backend API:", body_style
    ))
    
    fe_env_content = [[
        Paragraph("<font face='Courier' color='#FFFFFF' size='8'>"
                  "# Frontend API URL configuration (Point to local or deployed backend API)<br/>"
                  "VITE_API_BASE_URL=http://localhost:8000/api/v1"
                  "</font>", table_body_bold_style)
    ]]
    t_fe_env = Table(fe_env_content, colWidths=[415])
    t_fe_env.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#2D3748")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#1A202C")),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_fe_env)
    story.append(Spacer(1, 15))

    story.append(Paragraph("5.5 Service Initialization & Launch Commands", h2_style))
    story.append(Paragraph(
        "To start the system, open PowerShell terminal windows in the respective workspaces:", body_style
    ))
    
    start_content = [[
        Paragraph("<font face='Courier' color='#FFFFFF' size='8'>"
                  "# BACKEND COMMANDS (FastAPI)<br/>"
                  "cd lumia_retrieval_bert<br/>"
                  "./setup_local.ps1 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# Initialize venv and packages<br/>"
                  "venv/Scripts/activate &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# Activate virtual env<br/>"
                  "python migrate.py &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# Run schema migrations<br/>"
                  "python create_admin.py &nbsp;&nbsp;&nbsp;&nbsp;# Seed default admin accounts<br/>"
                  "uvicorn app.main:app --reload # Start web backend API<br/>"
                  "<br/>"
                  "# FRONTEND COMMANDS (Vue/Vite)<br/>"
                  "cd lumia_frontend_sample<br/>"
                  "npm install &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# Install Node modules<br/>"
                  "npm run dev &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# Run dev compilation server"
                  "</font>", table_body_bold_style)
    ]]
    t_start = Table(start_content, colWidths=[415])
    t_start.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#2D3748")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#1A202C")),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_start)
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 10: INSTALLATION GUIDE (POSTGRESQL & MAINTENANCE)
    # ════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("5.6 Production Deployment & PostgreSQL Migration", h2_style))
    story.append(Paragraph(
        "To support multi-user network deployment and prevent SQLite file locking, migrating to a "
        "central PostgreSQL database is required. Provision a PostgreSQL instance (e.g., on Railway, Supabase, or self-hosted) and modify the "
        "<code>DATABASE_URL</code> to: <code>postgresql://username:password@host:port/database</code>. "
        "Run the schema migrations script (<code>migrate.py</code>) on deployment to recreate all table schemas on PostgreSQL.", body_style
    ))
    
    story.append(Paragraph("5.7 Maintenance and Reset Operations", h2_style))
    story.append(Paragraph(
        "If you need to clear the vector database collections or purge uploaded PDF files during system initialization, run the reset utility script in the backend directory:", body_style
    ))
    story.append(Paragraph("<code>python reset_storage.py</code>", bullet_style))
    story.append(Paragraph(
        "This script purges all physical files in the <code>uploads/</code> directory, resets SQLite/PostgreSQL table schemas, "
        "and completely deletes/recreates the vector collections in Qdrant.", body_style
    ))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 11: TROUBLESHOOTING GUIDE
    # ════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("6. Technical Troubleshooting Guide", h1_style))
    story.append(Paragraph(
        "For system administrators deploying or evaluating the system, use the reference matrix below "
        "to resolve common environmental and service configuration errors:", body_style
    ))
    story.append(Spacer(1, 5))

    # Width: 415. Col widths: 95, 100, 220
    trouble_data = [
        [
            Paragraph("Error / Symptom", table_header_style),
            Paragraph("Probable Cause", table_header_style),
            Paragraph("Actionable Resolution", table_header_style)
        ],
        [
            Paragraph("<b>PDFInfoNotInstalledError</b><br/>or OCR fails to render pages.", table_body_bold_style),
            Paragraph("The <code>poppler</code> PDF utility binaries are not installed or not configured in system environment variables.", table_body_style),
            Paragraph("Download Poppler Windows binaries, extract files, and append the absolute path of the <code>/bin</code> folder to the system's PATH. Restart terminal sessions.", table_body_style)
        ],
        [
            Paragraph("<b>TesseractNotFoundError</b><br/>or text extraction fails.", table_body_bold_style),
            Paragraph("The <code>tesseract-ocr</code> executable is missing or not configured in system PATH.", table_body_style),
            Paragraph("Install the Tesseract OCR application. Add its installation folder (typically <code>C:\\Program Files\\Tesseract-OCR</code>) to the system environment PATH. Restart terminals.", table_body_style)
        ],
        [
            Paragraph("<b>ConnectError [Errno 111]</b><br/>or port 6333 Refused.", table_body_bold_style),
            Paragraph("Qdrant service is inactive or network port binding is blocked.", table_body_style),
            Paragraph("Ensure the Qdrant Docker container is running (<code>docker start qdrant</code>) or double-check local folder permissions if running Qdrant in file-storage mode.", table_body_style)
        ],
        [
            Paragraph("<b>OperationalError</b><br/>(no such table / columns).", table_body_bold_style),
            Paragraph("Relational database schemas are not initialized or out of sync.", table_body_style),
            Paragraph("Run the SQLAlchemy schema migration command in backend: <code>python migrate.py</code>. This creates SQLite file structure or PostgreSQL tables.", table_body_style)
        ],
        [
            Paragraph("<b>CORS Errors / API Failures</b><br/>on frontend console.", table_body_bold_style),
            Paragraph("The backend FastAPI host differs from the <code>VITE_API_BASE_URL</code> environment setup.", table_body_style),
            Paragraph("Verify FastAPI is active. Align frontend `.env` config (e.g., <code>VITE_API_BASE_URL=http://localhost:8000/api/v1</code>) with backend settings. Restart Vite dev server.", table_body_style)
        ]
    ]

    t_trouble = Table(trouble_data, colWidths=[95, 100, 220])
    t_trouble.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), brand_primary),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#F1F8F5"), colors.HexColor("#E8F5E9")]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_trouble)
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 12: TECHNICAL SUPPORT & GLOSSARY
    # ════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("7. Technical Support & Authors", h1_style))
    
    # Width: 415. Col widths: 138, 138, 139
    proponent_details = [
        [Paragraph("<b>Proponent Names</b>", table_header_style), Paragraph("<b>Academic Department</b>", table_header_style), Paragraph("<b>Project Roles</b>", table_header_style)],
        [Paragraph("Ryan Andrew A. Reyes", table_body_style), Paragraph("Computer Studies Department", table_body_style), Paragraph("BERT-NLP Integration & Database Admin", table_body_style)],
        [Paragraph("Maria Maneluz A. Orang", table_body_style), Paragraph("Computer Studies Department", table_body_style), Paragraph("Frontend Development (Vue 3/Vite) & UI", table_body_style)],
        [Paragraph("Prince Isiah R. Billones", table_body_style), Paragraph("Computer Studies Department", table_body_style), Paragraph("OCR Parsing Pipeline & Document Indexing", table_body_style)]
    ]
    t_prop = Table(proponent_details, colWidths=[138, 138, 139])
    t_prop.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), brand_primary),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#F1F8F5"), colors.HexColor("#E8F5E9")]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_prop)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("8. Glossary & Appendices", h1_style))
    story.append(Paragraph("<b>IMRAD:</b> Introduction, Methodology, Results, and Discussion. A standard formatting structure for scientific research papers, capstones, and theses.", bullet_style))
    story.append(Paragraph("<b>BERT-NLP:</b> Bidirectional Encoder Representations from Transformers. A transformer-based machine learning technique for natural language processing pre-training developed by Google, used here to build semantic embeddings of paper sections.", bullet_style))
    story.append(Paragraph("<b>Qdrant:</b> A production-ready vector database and vector similarity search engine, used here to index and search high-dimensional IMRAD section vectors.", bullet_style))
    story.append(Paragraph("<b>JWT:</b> JSON Web Token. An open standard for securely transmitting information between parties as a JSON object, used for user authentication.", bullet_style))
    story.append(Paragraph("<b>OCR:</b> Optical Character Recognition. The electronic conversion of images of typed, handwritten or printed text into machine-encoded text, using Tesseract and Poppler here.", bullet_style))
    story.append(Paragraph("<b>Vector Embeddings:</b> Numerical representations of text semantics in a high-dimensional vector space, allowing mathematical calculation of semantic similarity.", bullet_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated PDF manual at {filename}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        build_pdf(sys.argv[1])
    else:
        build_pdf()
