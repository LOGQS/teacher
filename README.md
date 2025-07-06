# AI-Powered Educational Presentation System

A comprehensive AI-driven platform for automatically generating interactive educational presentations with voice narration, real-time Q&A capabilities, and professional PowerPoint output.

## 🌟 Features

- **AI Course Generation**: Automatically creates structured courses from any topic using Gemini AI
- **Interactive Presentations**: Real-time voice Q&A during presentations with AI teacher responses
- **Multi-Modal Content**: Combines text, images, audio narration, and visual layouts
- **PowerPoint Export**: Generates professional `.pptx` files with embedded content
- **Real-Time Progress**: Live progress tracking with detailed statistics during generation
- **Session Management**: Organized file structure with course library and export capabilities

## 🚀 Tech Stack

**Backend:**
- Flask + SocketIO for real-time communication
- Google Gemini AI for content generation and conversation
- python-pptx for PowerPoint creation
- pyttsx3 for text-to-speech synthesis
- Groq API for speech-to-text transcription

**Frontend:**
- React with modern hooks and state management
- Tailwind CSS + Framer Motion for animations
- Real-time WebSocket updates
- Responsive design with dark theme

## 🛠️ Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   npm install  # in frontend directory
   ```

2. **Set environment variables:**
   ```bash
   export GEMINI_API_KEY="your_gemini_api_key"
   export GROQ_API_KEY="your_groq_api_key"  # optional, for STT
   ```

3. **Run the application:**
   ```bash
   npm start      # Runs concurrently
   ```

## 📋 Usage

1. **Generate Course**: Enter a topic, select complexity level and duration
2. **Real-time Generation**: Watch live progress as AI creates your presentation
3. **Interactive Learning**: Present with voice Q&A capabilities
4. **Export & Share**: Download PowerPoint files or save to library

## 🔮 Future Integration

This system will be integrated as a specialized subsystem within **ATLAS2** - a next-generation AI platform. The ATLAS2 integration will feature:

- Extended educational AI features - video generation...
- Integration with other ATLAS2 subsystems
- ...

---

*Current version represents the foundation implementation. The ATLAS2 integration will provide significant improvements in AI capabilities, performance, and feature set.*
