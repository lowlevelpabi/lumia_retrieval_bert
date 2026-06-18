import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
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
    on all pages except the cover page.
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
        # Margins: L: 1.5 in (108 pt), R: 1 in (72 pt). Width: 612 pt.
        # Header text starts at x=108 and ends at x=540 (612-72)
        self.setFont(font_bold, 8)
        self.setFillColor(colors.HexColor("#000000"))
        self.drawString(108, 752, "SMART RESEARCH")
        
        self.setFont(font_name, 8)
        self.setFillColor(colors.HexColor("#4A5568"))
        self.drawRightString(540, 752, "User & Technical Operation Manual")
        
        # Header Line
        self.setStrokeColor(colors.HexColor("#A0AEC0"))
        self.setLineWidth(0.75)
        self.line(108, 744, 540, 744)
        
        # ─── FOOTER ───
        self.setFont(font_name, 8)
        self.setFillColor(colors.HexColor("#4A5568"))
        self.drawString(108, 42, "Department of Computer Studies | Academic Year 2025-2026")
        
        text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(540, 42, text)
        
        # Footer Line
        self.setStrokeColor(colors.HexColor("#A0AEC0"))
        self.setLineWidth(0.5)
        self.line(108, 54, 540, 54)
        
        self.restoreState()

def build_pdf(filename="SMART_RESEARCH_User_Manual.pdf"):
    # Target dimensions: Letter page size (8.5 x 11 in) = 612 x 792 pt
    # Printable area: Left Margin 1.5 in (108 pt), other margins 1 in (72 pt) -> printable width = 432 pt
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=108,
        rightMargin=72,
        topMargin=72,
        bottomMargin=72
    )

    styles = getSampleStyleSheet()
    
    # ─── CUSTOM STYLES ───
    primary_color = colors.HexColor("#000000")   # Pure Black
    secondary_color = colors.HexColor("#1A202C") # Off-Black / Dark Charcoal
    text_color = colors.HexColor("#1A202C")      # Off-Black / Dark Charcoal
    light_text = colors.HexColor("#4A5568")      # Charcoal Grey

    title_style = ParagraphStyle(
        name='CoverTitle',
        fontName=font_bold,
        fontSize=20,
        leading=26,
        alignment=1, # Center
        textColor=primary_color,
        spaceAfter=22
    )
    
    subtitle_style = ParagraphStyle(
        name='CoverSubtitle',
        fontName=font_name,
        fontSize=12,
        leading=16,
        alignment=1, # Center
        textColor=secondary_color,
        spaceAfter=80
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
        textColor=primary_color,
        spaceAfter=11
    )

    h1_style = ParagraphStyle(
        name='Heading1_Custom',
        fontName=font_bold,
        fontSize=16,
        leading=20,
        textColor=primary_color,
        spaceBefore=22,
        spaceAfter=22,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        name='Heading2_Custom',
        fontName=font_bold,
        fontSize=13,
        leading=17,
        textColor=secondary_color,
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
        spaceAfter=22 # Double Spacing between bullets
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
        textColor=colors.HexColor("#1A202C")
    )

    story = []

    # ════════════════════════════════════════════════════════════════════════
    # ════════════════════════════════════════════════════════════════════════
    # PAGE 1: COVER PAGE
    # ════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 20))
    
    # Decorative color bar at the top
    dec_bar = Table([[""]], colWidths=[432], rowHeights=[6])
    dec_bar.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), secondary_color),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(dec_bar)
    story.append(Spacer(1, 20))

    # Main Title
    title_text = "SMART RESEARCH: AN AI-POWERED WEB-BASED RESEARCH PAPER RETRIEVAL AND RECOMMENDATION SYSTEM USING BERT-NLP"
    story.append(Paragraph(title_text, title_style))
    story.append(Spacer(1, 5))

    # Subtitle
    story.append(Paragraph("USER & TECHNICAL OPERATION MANUAL", subtitle_style))
    
    story.append(Spacer(1, 30))
    
    # Metadata Block
    story.append(Paragraph("<b>DEPARTMENT:</b>", author_header_style))
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
    
    toc_data = [
        [Paragraph("<b>Document Section</b>", table_body_bold_style), Paragraph("<b>Page</b>", table_body_bold_style)],
        [Paragraph("Introduction", table_body_style), Paragraph("2", table_body_style)],
        [Paragraph("1. System Core Concept", table_body_style), Paragraph("3", table_body_style)],
        [Paragraph("2. User Privilege Matrix", table_body_style), Paragraph("4", table_body_style)],
        [Paragraph("3. Operations Guide for Students & General Users", table_body_style), Paragraph("4", table_body_style)],
        [Paragraph("4. Operations Guide for Faculty Members", table_body_style), Paragraph("6", table_body_style)],
        [Paragraph("5. Operations Guide for Administrators", table_body_style), Paragraph("7", table_body_style)],
        [Paragraph("6. Technical Deployment Manual (IT Staff)", table_body_style), Paragraph("8", table_body_style)],
        [Paragraph("7. Technical Troubleshooting Guide", table_body_style), Paragraph("11", table_body_style)],
        [Paragraph("8. Technical Support & Authors", table_body_style), Paragraph("12", table_body_style)],
    ]
    
    t_toc = Table(toc_data, colWidths=[362, 70])
    t_toc.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEBELOW', (0,0), (-1,0), 1, primary_color),
        ('LINEBELOW', (0,1), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_toc)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("Introduction", h1_style))
    intro_p1 = (
        "Welcome to the <b>Smart Research User & Technical Operation Manual</b>. This manual provides "
        "comprehensive documentation for understanding, using, and maintaining the Smart Research platform—an "
        "AI-powered, web-based capstone and thesis repository utilizing advanced <b>BERT-NLP semantic search</b> "
        "and IMRAD-aware structure extraction."
    )
    intro_p2 = (
        "This system replaces traditional keyword matching database lookups with deep natural language queries, allowing "
        "students, faculty, and researchers to locate academic documents based on contextual meaning rather than matching words. "
        "This document guides students through query techniques, faculty through document ingestion/OCR, admins through "
        "approvals, and IT administrators through server deployment, Qdrant configurations, and database migrations."
    )
    story.append(Paragraph(intro_p1, body_style))
    story.append(Paragraph(intro_p2, body_style))
    story.append(PageBreak())

    # Introduction to Core Concept
    story.append(Paragraph("1. System Core Concept", h1_style))
    concept_txt_1 = (
        "<b>SMART RESEARCH</b> is an advanced, AI-powered web-based research paper repository designed to catalog "
        "and retrieve institutional capstones and undergraduate thesis. Traditional search systems rely on database "
        "keyword matching, which limits searches to exact words. Smart Research resolves this by employing semantic vector "
        "search using <b>BERT-NLP</b> (via the <b>Sentence-Transformers</b> model: <i>multi-qa-MiniLM-L6-cos-v1</i>)."
    )
    concept_txt_2 = (
        "Additionally, the system utilizes a unique <b>IMRAD-Aware Retrieval strategy</b>. When research PDFs are uploaded, "
        "the backend runs Optical Character Recognition (OCR) and splits the extracted text into structural sections: "
        "<b>Introduction, Methods, Results, and Discussion (IMRAD)</b>. These sections are embedded as independent "
        "high-dimensional vectors in a local <b>Qdrant Vector Database</b>. This enables users to perform targeted semantic searches, "
        "such as querying specifically for a methodology or statistical technique."
    )
    story.append(Paragraph(concept_txt_1, body_style))
    story.append(Paragraph(concept_txt_2, body_style))
    
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 3: ROLES MATRIX & STUDENT USER OPERATIONS
    # ════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("2. User Privilege Matrix", h1_style))
    story.append(Paragraph(
        "Access to the system features is guarded by a role-based authentication model. Users are mapped to "
        "specific groups depending on academic roles.", body_style
    ))
    story.append(Spacer(1, 8))

    # Privilege Matrix Table
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

    # Width: 504. Col widths: 184, 100, 100, 120
    t_priv = Table(priv_data, colWidths=[162, 90, 90, 90])
    t_priv.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#F7FAFC"), colors.HexColor("#EDF2F7")]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_priv)
    story.append(Spacer(1, 15))

    story.append(Paragraph("3. Operations Guide for Students & General Users", h1_style))
    
    story.append(Paragraph("3.1 Registration & Authentication", h2_style))
    story.append(Paragraph(
        "Students access the web interface to research capstone repositories. To create an account, navigate to "
        "the <b>Register</b> portal (<code>reg_win.vue</code>), fill in the full name, student email, preferred "
        "username, and password. Access is restricted using secure industry-standard JWT tokens; attempts to access "
        "protected pages will automatically redirect to the login module (<code>auth_win.vue</code>).", body_style
    ))
    
    story.append(Paragraph("3.2 Hybrid Search and Section Filtering", h2_style))
    story.append(Paragraph(
        "On the <b>Explore Portal</b> (<code>explore_win.vue</code>), users enter search queries in the central search bar. "
        "The system executes a hybrid search: executing relational SQL <code>LIKE</code> matches alongside Qdrant semantic cosine scoring.", body_style
    ))
    story.append(Paragraph("&bull; <b>Target Section Dropdown:</b> Narrow your search to specific structural sections like <i>Methods</i> to find papers using specific frameworks, algorithms, or statistics.", bullet_style))
    story.append(Paragraph("&bull; <b>Academic Filters:</b> Refine queries by Department (e.g., BSCS, BSIT, BSCpE), Project Type (Capstone vs Thesis), or Publication Year (e.g., last 5 years).", bullet_style))
    
    story.append(Paragraph("3.3 Metadata Details & Recommendations", h2_style))
    story.append(Paragraph(
        "Selecting a result loads the <b>Paper Detail View</b> (<code>detail_win.vue</code>), showing abstract metadata, author lists, and "
        "citations. To help students find relevant references, the page computes **'Narrow Down' Recommendations**. This engine "
        "cross-references the methods vector of the current paper in Qdrant, listing top similar methodology-matched research.", body_style
    ))
    
    story.append(Paragraph("3.4 Research Paper Submission & Approval", h2_style))
    story.append(Paragraph(
        "Students are authorized to upload and submit their own research papers to the repository via the "
        "upload portal (<code>up_win.vue</code>). Submitted documents are marked as pending and will not "
        "be vectorized or visible in public searches until they are reviewed and approved by an administrator "
        "or authorized faculty member.", body_style
    ))
    
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 4: FACULTY OPERATIONS & ADMIN DASHBOARD
    # ════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("4. Operations Guide for Faculty Members", h1_style))
    story.append(Paragraph(
        "Faculty accounts have the administrative authority to ingest, edit, and index new student research "
        "papers into the repository.", body_style
    ))
    
    story.append(Paragraph("4.1 Guided 3-Step Upload Flow (OCR)", h2_style))
    story.append(Paragraph(
        "The **Upload Portal** (<code>up_win.vue</code>) walks faculty members through a structured wizard:", body_style
    ))
    
    story.append(Paragraph("<b>Step 1: Document Upload & Strategy Selection</b>", body_style))
    story.append(Paragraph(
        "Choose the PDF file to upload. Select the ingestion strategy:<br/>"
        "&bull; <i>Smart Extract (OCR):</i> Uses PDF-to-image conversion, PyTesseract OCR, and regex mapping to "
        "auto-extract title, year, department, authors, and structural IMRAD boundaries.<br/>"
        "&bull; <i>Manual Input:</i> Skips OCR processing for faster uploads, enabling pure manual form filling.", bullet_style
    ))
    
    story.append(Paragraph("<b>Step 2: Thumbnail Review & Page Selection</b>", body_style))
    story.append(Paragraph(
        "The UI displays generated previews of the PDF pages. Review these previews side-by-side with the "
        "extracted text. Checkboxes allow you to deselect 'noise pages' (like certificate of approval pages, "
        "dedications, or cover sheets) to prevent useless words from contaminating the vector embeddings in Qdrant.", bullet_style
    ))
    
    story.append(Paragraph("<b>Step 3: Metadata Audit & Vector Indexing</b>", body_style))
    story.append(Paragraph(
        "Review the extracted values. If the OCR failed to read specific values (e.g. handwritten names or obscure years), "
        "the field will prompt with a warning placeholder. Faculty must manually type these corrections. The system uses "
        "the <code>|</code> pipe delimiter to register authors (e.g., <code>REYES, RYAN ANDREW A.|ORANG, MARIA MANELUZ A.</code>) "
        "to ensure Filipino name formats are properly logged. Click <b>Submit and Index</b> to push vectors to Qdrant.", bullet_style
    ))

    # Note / Tip Box using single cell table
    note_content = [
        [Paragraph("<b>💡 TIP: Page Selection Accuracy</b><br/>"
                   "Deselecting non-academic content pages (e.g., acknowledgement lists, references) in Step 2 directly "
                   "improves the semantic retrieval accuracy of the system, since only pure technical information will be vectorized.", callout_style)]
    ]
    t_note = Table(note_content, colWidths=[432])
    t_note.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F7FAFC")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#A0AEC0")),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(Spacer(1, 8))
    story.append(t_note)
    story.append(Spacer(1, 15))

    story.append(Paragraph("5. Operations Guide for Administrators", h1_style))
    story.append(Paragraph(
        "Administrator credentials allow access to the <b>Management Deck</b> (<code>manage_win.vue</code>) "
        "to oversee systems operations.", body_style
    ))
    
    story.append(Paragraph("5.1 Dashboard Analytics", h2_style))
    story.append(Paragraph(
        "View graphs, counts, and performance metrics including pending approval queues, "
        "total vectorized documents in Qdrant, and system user totals.", body_style
    ))
    
    story.append(Paragraph("5.2 User Management & Approvals", h2_style))
    story.append(Paragraph(
        "Approve new account signups, upgrade accounts to Faculty or Admin access levels, and manage "
        "pending student research upload requests in the queue.", body_style
    ))
    
    story.append(Paragraph("5.3 Audit Log Monitor", h2_style))
    story.append(Paragraph(
        "The admin dashboard streams live records from the <code>activity_logs</code> database table, capturing "
        "actions performed (such as uploads, deletions, database updates) indicating the operator, role, and exact timestamp.", body_style
    ))
    
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 5: TECHNICAL SETUP & DEPLOYMENT
    # ════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("6. Technical Deployment Manual (IT Staff)", h1_style))
    story.append(Paragraph(
        "This section guides the network administrator through deploying and configuring the system.", body_style
    ))
    
    story.append(Paragraph("6.1 Prerequisite Installations", h2_style))
    story.append(Paragraph(
        "Before setting up the repositories, install the following external system-level binaries:", body_style
    ))
    story.append(Paragraph("1. <b>Tesseract OCR:</b> Download the Windows installer from UB-Mannheim Tesseract. Install and add the install directory path to the system's Environment <code>PATH</code>.", bullet_style))
    story.append(Paragraph("2. <b>Poppler Library:</b> Extract Poppler Windows binaries. Add the <code>/bin</code> subdirectory to the system's Environment <code>PATH</code>. (Required for PDF thumbnail rendering).", bullet_style))
    story.append(Paragraph("3. <b>Node.js:</b> Install LTS version 20 or higher.", bullet_style))
    story.append(Paragraph("4. <b>Python:</b> Install Python version 3.10 or higher.", bullet_style))
    story.append(Paragraph("5. <b>Docker:</b> Recommended for running a production instance of Qdrant Vector Database.", bullet_style))
    
    story.append(Paragraph("6.2 Qdrant Vector Database Setup", h2_style))
    story.append(Paragraph(
        "Qdrant stores the 6-vector IMRAD schema. For local testing, it runs in file-storage mode. For production, run the Docker image:", body_style
    ))
    
    # Code snippet block
    code_content = [[
        Paragraph("<font face='Courier' color='#FFFFFF' size='8'>"
                  "docker run -d -p 6333:6333 -p 6334:6334 \\<br/>"
                  "&nbsp;&nbsp;-v qdrant_storage:/qdrant/storage \\<br/>"
                  "&nbsp;&nbsp;qdrant/qdrant"
                  "</font>", table_body_bold_style)
    ]]
    t_code = Table(code_content, colWidths=[432])
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

    story.append(Paragraph("6.3 Backend Environment Configuration (FastAPI)", h2_style))
    story.append(Paragraph(
        "Create a <code>.env</code> file in the backend root directory <code>lumia_retrieval_bert</code>:", body_style
    ))
    
    env_content = [[
        Paragraph("<font face='Courier' color='#FFFFFF' size='8'>"
                  "# Relational database (Default SQLite for dev, PostgreSQL for production)<br/>"
                  "DATABASE_URL=sqlite:///./thesis.db<br/>"
                  "# Vector database configuration<br/>"
                  "QDRANT_URL=http://localhost:6333<br/>"
                  "# Evaluation settings<br/>"
                  "ENABLE_SAMPLE_DOCS=false"
                  "</font>", table_body_bold_style)
    ]]
    t_env = Table(env_content, colWidths=[432])
    t_env.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#2D3748")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#1A202C")),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_env)
    story.append(Spacer(1, 8))

    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 6: LAUNCHING, MAINTENANCE & TROUBLESHOOTING
    # ════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("6.4 Service Initialization commands", h2_style))
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
    t_start = Table(start_content, colWidths=[432])
    t_start.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#2D3748")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#1A202C")),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_start)
    story.append(Spacer(1, 15))

    story.append(Paragraph("6.5 Production Deployment & PostgreSQL Migration", h2_style))
    story.append(Paragraph(
        "To support multi-user network deployment and prevent file locking, migrating from SQLite to a "
        "central PostgreSQL database is required. Provision a PostgreSQL instance and modify the "
        "<code>DATABASE_URL</code> to: <code>postgresql://username:password@host:port/database</code>. "
        "Run the migrations script (<code>migrate.py</code>) on deployment to recreate tables on PostgreSQL.", body_style
    ))
    
    story.append(Paragraph("6.6 Maintenance and Reset Operations", h2_style))
    story.append(Paragraph(
        "If you need to clear the vector index collection or purge files during system initialization, run the reset utility script:", body_style
    ))
    story.append(Paragraph("<code>python reset_storage.py</code>", bullet_style))
    story.append(Paragraph(
        "This script purges files in the <code>uploads/</code> directory, resets SQLite/PostgreSQL paper lists, "
        "and completely deletes/recreates the Qdrant collections.", body_style
    ))
    
    story.append(PageBreak())
    story.append(Paragraph("7. Technical Troubleshooting Guide", h1_style))
    story.append(Paragraph(
        "For system administrators deploying or evaluating the system, use the reference matrix below "
        "to resolve common environmental and service configuration errors:", body_style
    ))
    story.append(Spacer(1, 5))

    trouble_data = [
        [
            Paragraph("Error / Symptom", table_header_style),
            Paragraph("Probable Cause", table_header_style),
            Paragraph("Actionable Resolution", table_header_style)
        ],
        [
            Paragraph("<b>PDFInfoNotInstalledError</b><br/>or OCR fails to render pages.", table_body_bold_style),
            Paragraph("The <code>poppler</code> PDF utility binaries are not installed or not configured in system environment variable path.", table_body_style),
            Paragraph("Download Poppler Windows binaries, extract files, and append the absolute path of the <code>/bin</code> folder to the system's PATH variable. Restart terminal sessions.", table_body_style)
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
            Paragraph("The backend FastAPI host differs from the <code>VITE_API_URL</code> environment setup.", table_body_style),
            Paragraph("Verify FastAPI is active. Align frontend `.env` config (e.g., <code>VITE_API_URL=http://127.0.0.1:8000</code>) with backend host settings. Restart Vite dev server.", table_body_style)
        ]
    ]

    t_trouble = Table(trouble_data, colWidths=[100, 112, 220])
    t_trouble.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), secondary_color),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#F7FAFC"), colors.HexColor("#EDF2F7")]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_trouble)

    story.append(Spacer(1, 15))
    story.append(Paragraph("8. Technical Support & Authors", h1_style))
    
    proponent_details = [
        [Paragraph("<b>Proponent Names</b>", table_header_style), Paragraph("<b>Academic Department</b>", table_header_style), Paragraph("<b>Project Roles</b>", table_header_style)],
        [Paragraph("Ryan Andrew A. Reyes", table_body_style), Paragraph("Computer Studies Department", table_body_style), Paragraph("BERT-NLP Integration & Database Admin", table_body_style)],
        [Paragraph("Maria Maneluz A. Orang", table_body_style), Paragraph("Computer Studies Department", table_body_style), Paragraph("Frontend Development (Vue 3/Vite) & UI", table_body_style)],
        [Paragraph("Prince Isiah R. Billones", table_body_style), Paragraph("Computer Studies Department", table_body_style), Paragraph("OCR Parsing Pipeline & Document Indexing", table_body_style)]
    ]
    t_prop = Table(proponent_details, colWidths=[144, 144, 144])
    t_prop.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#F7FAFC"), colors.HexColor("#EDF2F7")]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_prop)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated PDF manual at {filename}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        build_pdf(sys.argv[1])
    else:
        build_pdf()
