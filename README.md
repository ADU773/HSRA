# 🗑️ TrashGuard — Hazardous Scene Recognition & Analytics (HSRA)

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black" />
  <img src="https://img.shields.io/badge/Flask-3.0-000000?logo=flask&logoColor=white" />
  <img src="https://img.shields.io/badge/YOLOv11-Ultralytics-purple" />
  <img src="https://img.shields.io/badge/License-MIT-green" />
</p>

> **TrashGuard** is a full-stack AI-powered video analytics system designed to detect trash-throwing incidents in real time. It combines custom-trained YOLO object detection, BoT-SORT multi-object tracking, and a Vision-Language Model (VLM) for semantic scene verification — all wrapped in a modern React dashboard.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🎯 **Custom Trash Detection** | Fine-tuned YOLOv11 model (`best.pt`) to detect thrown trash objects |
| 👤 **Multi-Object Tracking** | BoT-SORT tracker for persons and vehicles across video frames |
| 🧠 **VLM Semantic Analysis** | Vision-Language Model describes scenes and verifies incidents |
| 📊 **Real-Time Progress** | SSE (Server-Sent Events) stream shows live analysis progress in the UI |
| 📄 **Professional PDF Reports** | ReportLab-powered paginated reports with incident logs & VLM timelines |
| 🏛️ **Historical Data Center** | Browse all past inference logs globally |
| 📥 **CSV Export** | Download raw tracking data for further analysis |

---

## 🏗️ Project Architecture

```
HSRA/
├── backend/                  # Flask API + AI inference engine
│   ├── app.py                # Main Flask server & REST endpoints
│   ├── analyzer.py           # Core video analysis pipeline (YOLO + BoT-SORT + VLM)
│   ├── pdf_report.py         # ReportLab PDF report generator
│   ├── report.py             # Report data aggregation utilities
│   ├── vlm_helper.py         # Vision-Language Model interface
│   └── requirements.txt      # Python dependencies
│
├── frontend-react/           # React + Vite + Tailwind CSS dashboard
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx       # Upload & live progress view
│   │   │   ├── AnalysisReport.jsx  # Full analysis report viewer
│   │   │   └── DataCenter.jsx      # Historical inference logs
│   │   ├── components/
│   │   │   ├── Sidebar.jsx         # Navigation sidebar
│   │   │   ├── Topbar.jsx          # Top navigation bar
│   │   │   ├── UploadSection.jsx   # Drag-and-drop video upload
│   │   │   ├── FrameGallery.jsx    # Detected frame thumbnails
│   │   │   ├── TracksTable.jsx     # Object tracking data table
│   │   │   ├── VlmDescriptions.jsx # VLM scene descriptions
│   │   │   ├── CLIPVerification.jsx# CLIP-based verification display
│   │   │   └── Toast.jsx           # Notification toasts
│   │   └── api.js                  # Axios API client + SSE helper
│   └── package.json
│
├── best.pt                   # Custom-trained trash detection model (YOLOv11)
├── yolo11n.pt                # Standard YOLOv11n for person/vehicle detection
├── start.bat                 # One-click backend startup script (Windows)
└── start_react.bat           # One-click full-stack startup script (Windows)
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+** with pip
- **Node.js 18+** with npm
- **Git**
- *(Optional)* NVIDIA GPU with CUDA for faster inference
- *(Optional)* [Ollama](https://ollama.ai/) for local VLM support

---

### 1. Clone the Repository

```bash
git clone https://github.com/ADU773/HSRA.git
cd HSRA
```

---

### 2. Backend Setup

```bash
cd backend

# Create and activate a virtual environment (recommended)
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install Python dependencies
pip install -r requirements.txt
```

#### Configure Environment Variables

Create a `.env` file inside the `backend/` directory:

```env
# backend/.env

# Set to "true" to enable Ollama VLM integration
USE_OLLAMA=false

# Ollama model name (if USE_OLLAMA=true)
OLLAMA_MODEL=moondream

# Flask secret key
SECRET_KEY=your-secret-key-here
```

#### Start the Backend Server

```bash
# From the backend/ directory
python app.py
```

The API will be available at **http://localhost:5000**

---

### 3. Frontend Setup

```bash
cd frontend-react

# Install Node dependencies
npm install

# Start the development server
npm run dev
```

The React app will be available at **http://localhost:5173**

---

### 4. One-Click Startup (Windows)

From the project root, double-click or run:

```bat
# Backend only
start.bat

# Full stack (backend + frontend)
start_react.bat
```

---

## 🔌 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/upload` | Upload a video for analysis |
| `GET` | `/api/progress/{job_id}` | SSE stream for real-time progress |
| `GET` | `/api/report/{job_id}` | Fetch completed analysis report (JSON) |
| `GET` | `/api/report/{job_id}/pdf` | Download generated PDF report |
| `GET` | `/api/report/{job_id}/csv` | Download raw tracking data (CSV) |
| `GET` | `/api/logs` | Fetch all historical inference logs |

---

## 🤖 Models

### Custom Trash Detection — `best.pt`
A YOLOv11 model fine-tuned on a custom dataset to detect thrown litter and waste objects.

### General Object Detection — `yolo11n.pt`
Standard YOLOv11 nano model used to track persons and vehicles through scenes for contextual understanding.

### Vision-Language Model (VLM)
- **Local**: Uses [Ollama](https://ollama.ai/) with `moondream` (or another supported model) for zero-cost, private inference.
- Set `USE_OLLAMA=true` in `.env` to enable.

---

## 📊 Analysis Report Sections

After video processing completes, the React dashboard renders:

1. **Summary Statistics** — total detections, incident count, FPS, duration
2. **Incident Log** — timestamped table of each detected trash-throwing event
3. **Frame Gallery** — key annotated frames from the video
4. **Object Tracking Registry** — full BoT-SORT tracking table per object ID
5. **VLM Semantic Timeline** — plain-language descriptions for each scene segment
6. **CLIP Verification** — confidence scores for semantic verification
7. **PDF Export** — downloadable, paginated professional report

---

## 🛠️ Tech Stack

### Backend
- **Flask 3** — REST API server
- **Ultralytics YOLOv11** — object detection & segmentation
- **OpenCV** — video decoding and frame processing
- **PyTorch** — model inference
- **ReportLab** — PDF generation
- **Pandas** — data aggregation & CSV export
- **Transformers / HuggingFace** — VLM integration

### Frontend
- **React 18** — UI framework
- **Vite** — build tool & dev server
- **Tailwind CSS** — utility-first styling
- **Axios** — HTTP client
- **Server-Sent Events (SSE)** — real-time progress streaming

---

## 📁 Data & Privacy

- Uploaded videos are processed locally and stored in `backend/uploads/` temporarily.
- No data is sent to external servers unless a cloud-based VLM endpoint is configured.
- The `.env` file is excluded from version control — never commit secrets.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'Add your feature'`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 👤 Author

**ADU773** — [GitHub Profile](https://github.com/ADU773)

---

<p align="center">Built with ❤️ using Flask, React, and YOLOv11</p>
