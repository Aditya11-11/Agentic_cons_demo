---
title: Voice Support Copilot
emoji: 🎧
colorFrom: blue
colorTo: indigo
sdk: docker
app_file: app.py
pinned: false
---

# Voice Support Copilot

An AI-powered support assistant that listens, thinks, and speaks.

## Features
- **Voice Support**: Live speech-to-text (Vosk) and neural text-to-speech (Edge-TTS).
- **Brain**: Powered by `Qwen3-1.7B`.
- **Knowledge**: Uses RAG with ChromaDB to answer from documents.

## Quick Start
1. **Build**: `docker build -t support-copilot .`
2. **Run**: `docker run -it support-copilot`
3. **Use**: Type `v` for voice mode or just type your question.

## Project Structure
- `main.py`: App entry point.
- `engine_arc/`: Core logic for LLM, Voice, and RAG.


## Setup
- Follow the instructions in `setup.md`