You are a senior desktop application product designer and Python engineer.

I want you to design and implement the COMPLETE UI/UX and frontend application for a standalone macOS desktop application.

IMPORTANT:
This is NOT a web application.

Do NOT use React, Vite, Next.js, Tailwind CSS, shadcn/ui, or other web-first frontend technologies.

The application must be designed as a real native-style desktop application because the future application will contain a local document rendering engine, image processing, handwriting analysis/rendering, PDF generation, batch processing, and potentially local ML components.

==================================================
PROJECT NAME
==================================================

Handwriting Document Generator

==================================================
PROJECT OVERVIEW
==================================================

This is a standalone local macOS desktop application for generating printable documents from editable templates.

The application will eventually connect to a local Python rendering/processing engine that can work with handwriting-style profiles created from user-provided handwriting samples.

The frontend/UI must therefore be designed around a future local Python processing engine.

The UI should currently use realistic mock/sample data so that the complete application can be developed and tested before the actual rendering engine is integrated.

The application should feel like a polished professional Mac desktop application, NOT like a website or generic admin dashboard.

==================================================
CORE USER CAPABILITIES
==================================================

The user should be able to:

- Manage handwriting profiles/styles
- Add and manage handwriting samples
- Review handwriting analysis status
- Create and edit document templates
- Work with 4×6 inch document templates
- Work with #10 envelope templates
- Enter and edit document content
- Import structured TXT/CSV data
- Preview documents
- Generate documents in batches
- Monitor batch generation progress
- Review generated files
- Manage export history
- Configure application settings
- Manage local application data

IMPORTANT SCOPE BOUNDARY:

The application must remain a general-purpose legitimate document-generation and printing tool.

Do not design functionality specifically intended to bypass promotion/sweepstakes rules, disguise bulk submissions, or defeat anti-abuse systems.

==================================================
TECHNOLOGY STACK
==================================================

Use a Python-first native desktop architecture.

PRIMARY LANGUAGE:

Python 3.12+

DESKTOP UI:

PySide6 / Qt 6

Use Qt Designer concepts where useful, but prefer maintainable Python-based UI components and layouts.

RENDERING:

- Pillow
- NumPy

IMAGE PROCESSING:

- OpenCV only where technically necessary

PDF GENERATION:

- ReportLab

LOCAL DATABASE:

- SQLite
- SQLAlchemy if an ORM is useful

DATA VALIDATION:

- Pydantic

APPLICATION SETTINGS:

- JSON/config files where appropriate

TESTING:

- pytest

PACKAGING:

- PyInstaller

MACOS:

The final application must be designed for packaging as a standalone macOS .app application.

The architecture should be compatible with both Apple Silicon and Intel Macs where practical.

==================================================
ARCHITECTURE
==================================================

Use a clean layered architecture.

Do NOT put business logic directly inside PySide6 widgets.

Use this conceptual architecture:

UI Layer
    ↓
Application / Service Layer
    ↓
Domain / Core Logic
    ↓
Rendering / Processing Engine
    ↓
Storage / File System

Recommended structure:

project/
│
├── app.py
│
├── ui/
│   ├── main_window.py
│   ├── layouts/
│   ├── components/
│   ├── dialogs/
│   └── pages/
│       ├── dashboard.py
│       ├── documents.py
│       ├── document_editor.py
│       ├── templates.py
│       ├── template_editor.py
│       ├── handwriting_profiles.py
│       ├── handwriting_detail.py
│       ├── batch_generator.py
│       ├── batch_progress.py
│       ├── exports.py
│       ├── settings.py
│       └── onboarding.py
│
├── core/
│   ├── document_engine.py
│   ├── template_engine.py
│   ├── batch_engine.py
│   ├── import_engine.py
│   └── export_engine.py
│
├── rendering/
│   ├── renderer.py
│   ├── text_renderer.py
│   ├── image_renderer.py
│   └── handwriting/
│       ├── profile.py
│       ├── analyzer.py
│       └── generator.py
│
├── services/
│   ├── handwriting_service.py
│   ├── template_service.py
│   ├── document_service.py
│   ├── batch_service.py
│   └── export_service.py
│
├── storage/
│   ├── database.py
│   ├── models.py
│   └── settings.py
│
├── templates/
│   ├── card_4x6.json
│   └── envelope_10.json
│
├── assets/
│   └── handwriting/
│
├── tests/
│
├── requirements.txt
└── README.md

Keep UI, services, domain logic, rendering, and persistence clearly separated.

==================================================
IMPORTANT ARCHITECTURAL REQUIREMENT
==================================================

The UI must NOT depend directly on the future handwriting engine.

For example:

UI
 ↓
HandwritingService
 ↓
HandwritingEngine

The initial frontend can use a MockHandwritingEngine.

Later we should be able to replace:

MockHandwritingEngine

with:

RealHandwritingEngine

without rewriting the UI.

Use interfaces/protocols or clean abstractions where appropriate.

The same principle should apply to:

- Document generation
- Template management
- Batch processing
- PDF export
- Data import

==================================================
DESIGN DIRECTION
==================================================

You decide the complete visual identity.

Do NOT ask me to choose:

- colors
- fonts
- spacing
- shadows
- borders
- icon style
- visual theme

Make those decisions yourself.

The application should feel:

- Premium
- Professional
- Modern
- Minimal
- Native to macOS
- Desktop-focused
- Reliable
- Technical but approachable
- Suitable for professional productivity software

Do NOT make it look like:

- A generic SaaS dashboard
- A web admin panel
- A mobile application
- An AI chatbot
- An overly colorful startup dashboard

Use:

- Strong hierarchy
- Clean typography
- Comfortable spacing
- Subtle borders
- Native-feeling controls
- Clear hover/focus states
- Professional dialogs
- Keyboard-friendly interactions
- Smooth but restrained animations/transitions

Avoid:

- Excessive gradients
- Huge decorative graphics
- Excessive rounded cards
- Visual clutter
- Excessive animations
- Giant dashboard statistics
- Mobile-first layouts

==================================================
MACOS DESKTOP EXPERIENCE
==================================================

Design the application specifically for desktop.

Support:

- Window resizing
- Small MacBook displays
- Large external monitors
- Retina displays
- Keyboard navigation
- Mouse interaction
- Trackpad interaction

Use appropriate desktop UI conventions.

The application should have:

- Persistent sidebar/navigation
- Toolbar
- Main workspace
- Contextual panels
- Dialogs
- Menus
- Keyboard shortcuts where appropriate

The UI should visually feel like a serious native Mac application.

==================================================
GLOBAL APPLICATION LAYOUT
==================================================

Create a persistent application shell.

LEFT SIDEBAR:

- App logo/name
- Dashboard
- Documents
- Templates
- Handwriting
- Batch Generator
- Exports
- Settings

Bottom:

- Help
- App version
- Local workspace/status

MAIN AREA:

- Page title
- Subtitle when needed
- Breadcrumb when useful
- Primary action
- Main content

The sidebar should be collapsible.

==================================================
PAGE 1 — DASHBOARD
==================================================

Create a professional application dashboard.

Header:

Dashboard

Subtitle explaining the application.

Primary actions:

- Create Document
- Start Batch

Overview:

- Handwriting Profiles
- Templates
- Documents Generated
- Recent Batches

Recent activity:

- Recent document generations
- Recently edited templates
- Recently imported datasets

Quick actions:

- New Document
- New Template
- Import Data
- Manage Handwriting
- Start Batch Generation

System status:

- Rendering Engine
- Local Storage
- Export System

Use realistic mock data.

Provide:

- Loading state
- Empty state
- Error state
- Populated state

==================================================
PAGE 2 — DOCUMENTS
==================================================

Create a document management interface.

Header:

Documents

Actions:

- Create Document
- Import
- Search
- Filter
- Sort

Show documents in a professional table/list.

Columns:

- Document name
- Template
- Handwriting profile
- Created date
- Status
- Export format
- Actions

Statuses:

- Draft
- Ready
- Generating
- Completed
- Failed

Actions:

- Open
- Duplicate
- Export
- Delete

Include:

- Search
- Filters
- Sorting
- Pagination or efficient list rendering
- Empty state
- Bulk selection

==================================================
PAGE 3 — DOCUMENT EDITOR
==================================================

This is one of the most important screens.

Create a professional document layout editor.

Use a three-panel workspace.

LEFT PANEL:

Document configuration.

Fields:

- Document name
- Template
- Handwriting profile
- Page size
- Orientation
- Margins
- Output format

CENTER:

Large document canvas.

Show realistic 4×6 document proportions.

The preview must maintain correct physical proportions.

Include:

- Zoom in
- Zoom out
- Fit to screen
- Zoom percentage
- Ruler
- Grid toggle
- Print-safe area
- Element boundaries
- Selection state

RIGHT PANEL:

Properties inspector.

When an element is selected:

- Text
- Handwriting profile
- Size
- Position
- Alignment
- Line spacing
- Letter spacing
- Opacity/ink intensity
- Rotation
- Visibility

Bottom toolbar:

- Save
- Save As
- Preview
- Export

The editor should feel similar to professional design/layout software.

==================================================
PAGE 4 — TEMPLATES
==================================================

Create template management.

Templates:

- 4×6 Card
- #10 Envelope

Each template card should show:

- Preview
- Name
- Dimensions
- Last modified
- Status

Actions:

- Edit
- Duplicate
- Rename
- Delete
- Use Template

Primary:

Create Template

==================================================
PAGE 5 — TEMPLATE EDITOR
==================================================

Create a visual template editor.

The user can configure:

- Canvas dimensions
- Text blocks
- Header
- Body
- Address blocks
- Data fields/placeholders
- Margins
- Alignment

CENTER:

Canvas workspace.

LEFT:

Element toolbox:

- Text
- Address
- Data Field
- Divider
- Image/Logo if supported

RIGHT:

Properties inspector:

- Content
- Position
- Width
- Height
- Alignment
- Size
- Style
- Visibility

Bottom:

- Save Template
- Preview
- Cancel

Make this feel like a real desktop design editor.

==================================================
PAGE 6 — HANDWRITING PROFILES
==================================================

Create handwriting profile management.

Header:

Handwriting Profiles

Primary:

Add Handwriting Profile

Each profile should show:

- Profile name
- Handwriting preview
- Number of samples
- Created date
- Status
- Default indicator

Statuses:

- Ready
- Processing
- Needs Review
- Error

Actions:

- Open
- Preview
- Rename
- Duplicate
- Delete

==================================================
PAGE 7 — HANDWRITING PROFILE DETAIL
==================================================

Create a detailed handwriting profile workspace.

Header:

Profile name

PROFILE OVERVIEW:

- Profile name
- Description
- Created date
- Status

SAMPLES:

Show uploaded handwriting sample thumbnails.

Actions:

- Add Sample
- Remove Sample
- Replace Sample

ANALYSIS:

Display mock/placeholder analysis:

- Character coverage
- Sample quality
- Stroke information
- Spacing analysis
- Slant analysis
- Baseline analysis

Example:

Analysis Status: Ready

Character Coverage: 92%

Samples Analyzed: 10

IMPORTANT:

Do not claim that the frontend itself trains an AI model.

The UI should display analysis information returned by the future local processing engine.

RENDERING PREVIEW:

Allow the user to enter sample text.

Show:

- Text input
- Preview canvas
- Variation controls
- Refresh Preview

Initially use mock rendering data.

==================================================
PAGE 8 — BATCH GENERATOR
==================================================

Create a multi-step batch-generation workflow.

STEP 1:

Select Template

Options:

- 4×6 Card
- #10 Envelope

STEP 2:

Select Handwriting Profile

STEP 3:

Import Data

Supported:

- TXT
- CSV

Show:

- File name
- Records detected
- Valid records
- Invalid records

Display data preview table.

STEP 4:

Configure Output

Options:

- Output format
- Output directory
- File naming pattern
- Individual files
- Combined PDF
- Include envelope
- Quality/resolution

STEP 5:

Review

Show sample previews.

Primary:

Start Generation

==================================================
PAGE 9 — BATCH GENERATION PROGRESS
==================================================

Create a dedicated processing screen.

Show:

Batch name

Overall progress

Generated

Remaining

Failed

Current item

Example:

72%

Generated: 720

Remaining: 280

Failed: 3

Current item: document_0721.pdf

Include:

- Progress bar
- Processing status
- Estimated remaining time
- Cancel
- View errors

Activity log:

- Document generated
- Document skipped
- Export completed
- Error encountered

Completion screen:

Generation Complete

Show:

- Total
- Successful
- Failed
- Output location

Actions:

- Open Output Folder
- View Results
- Generate Again

==================================================
PAGE 10 — EXPORTS
==================================================

Create export history.

Show:

- Batch name
- Date
- Number of files
- Format
- Status
- Output location

Actions:

- Open Folder
- View
- Export Again
- Delete History

Filters:

- Date
- Status
- Format

==================================================
PAGE 11 — SETTINGS
==================================================

Create professional settings.

GENERAL:

- Application workspace
- Default output directory
- Default template
- Default handwriting profile

APPEARANCE:

- Theme
- UI scale

GENERATION:

- Default export format
- Default resolution
- Batch preferences

STORAGE:

- Local data location
- Cache
- Clear cache

PRINTING:

- Default printer
- Page scaling
- Print margins

ABOUT:

- App version
- System information
- Documentation
- Support

==================================================
PAGE 12 — ONBOARDING
==================================================

First launch onboarding.

Step 1:

Welcome

Step 2:

Create/select workspace

Step 3:

Add handwriting profile

Step 4:

Create first template

Step 5:

Ready

Allow:

Skip Setup

Keep it short and professional.

==================================================
REUSABLE UI COMPONENTS
==================================================

Create reusable PySide6 components for:

- Sidebar
- Toolbar
- Header
- Breadcrumb
- Buttons
- Inputs
- Select controls
- Dropdowns
- Dialogs
- Drawers/panels
- Tooltips
- Tabs
- Cards
- Tables
- Empty states
- Error states
- Loading states
- Progress bars
- File picker
- Search
- Filters
- Confirmation dialogs
- Toast/notification system

Do not duplicate UI logic.

==================================================
APPLICATION STATES
==================================================

Every major page must support:

1. Loading
2. Empty
3. Populated
4. Error
5. Success

Do not design only the happy path.

==================================================
MOCK DATA
==================================================

Create realistic mock data for:

- Handwriting profiles
- Templates
- Documents
- Batch jobs
- Export history
- Sample analysis
- Rendering previews

The complete application should be navigable and functional using mock services.

==================================================
SERVICE ARCHITECTURE
==================================================

Create service interfaces/classes such as:

HandwritingService
TemplateService
DocumentService
BatchService
ExportService
ImportService

Initially provide mock implementations.

For example:

MockHandwritingService
MockTemplateService
MockDocumentService
MockBatchService
MockExportService

The UI must communicate with services rather than directly manipulating mock data.

Later the mock services can be replaced with real implementations.

==================================================
THREADING / LONG TASKS
==================================================

Because the final application will perform potentially expensive operations such as:

- Image processing
- Rendering
- PDF generation
- Batch processing
- Handwriting analysis

DO NOT block the PySide6 UI thread.

Design the architecture so long-running operations can use:

- QThread
- QThreadPool
- QRunnable
- Signals/slots

Use progress signals to update the UI.

The application must remain responsive during processing.

==================================================
FILE SYSTEM
==================================================

Use native macOS file dialogs where appropriate.

Support:

- Select folder
- Select file
- Save file
- Open output folder

Do not hardcode paths.

==================================================
PRINT PREVIEW
==================================================

The document preview must preserve physical proportions.

For example:

4×6 inch documents should visually maintain a 2:3 aspect ratio.

The UI should clearly distinguish:

- Document boundary
- Print-safe area
- Content area

The preview should support zooming without distorting the document.

==================================================
ACCESSIBILITY
==================================================

Implement:

- Keyboard navigation
- Keyboard shortcuts where appropriate
- Visible focus states
- Accessible labels
- Appropriate Qt accessibility properties
- Good contrast
- Tooltips
- Logical tab order

==================================================
ANIMATION
==================================================

Use subtle desktop-appropriate transitions.

Avoid excessive animation.

Prioritize performance and responsiveness.

==================================================
TESTING
==================================================

Create pytest tests for service/business logic.

At minimum test:

- Template loading
- Document creation
- Data validation
- TXT import
- CSV import
- Export configuration
- Batch state management
- Settings persistence

UI should be testable without the actual handwriting engine.

==================================================
PACKAGING
==================================================

Prepare the project for macOS packaging using PyInstaller.

The final structure should allow generation of:

Application.app

Do not assume that the user will have Python installed.

The final packaged application should contain all required runtime dependencies.

==================================================
FINAL DELIVERABLE
==================================================

Build the complete desktop UI with:

1. Dashboard
2. Documents
3. Document Editor
4. Templates
5. Template Editor
6. Handwriting Profiles
7. Handwriting Profile Detail
8. Batch Generator
9. Batch Progress
10. Exports
11. Settings
12. Onboarding
13. Reusable desktop components
14. Mock services
15. Mock data
16. Loading/empty/error/success states
17. Local file handling
18. Responsive desktop layouts
19. Service architecture
20. Thread-safe architecture for future rendering
21. Clean Python architecture
22. macOS packaging preparation

The application must look and behave like a real commercial Mac desktop application.

Do not simplify the Document Editor.

Do not simplify the Template Editor.

Do not remove the Handwriting Profile workflow.

Do not replace the Batch Generator with a simple form.

These are core parts of the product.

Before implementation, first establish the complete architecture and component hierarchy, then implement the application systematically.

Do not ask me to choose the visual design. Make professional design decisions yourself.

The most important priorities are:

1. Excellent desktop UX
2. Clean architecture
3. Future integration with the local Python rendering engine
4. Responsive UI during long-running operations
5. Accurate document preview and print dimensions
6. Maintainable production-quality code
7. Easy future macOS packaging