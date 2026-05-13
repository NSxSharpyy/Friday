# 🦾 F.R.I.D.A.Y. Mk-XXI: The Hybrid AI Operating Layer

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![UI](https://img.shields.io/badge/UI-PyQt6-cyan.svg)
![AI](https://img.shields.io/badge/AI-Groq%20%7C%20Ollama-orange.svg)

F.R.I.D.A.Y. is a next-generation Hybrid AI Desktop Assistant designed for seamless Human-Computer Interaction (HCI). It bridges the gap between high-speed Cloud Intelligence and local Data Privacy, providing a robust environment for automation and system management.

---

## 🚀 Core Capabilities

* **Hybrid Brain Engine:** A dynamic switching system that utilizes **Groq LPU** for low-latency cloud processing and **Ollama (Llama 3)** for 100% offline data sovereignty and edge computing.
* **Acoustic Activation Trigger:** Advanced sound frequency analysis allows the system to wake from background mode via a specific **Clap-Pattern**, minimizing CPU idle-state consumption.
* **Multimodal Vision Intelligence:**
    * **Dynamic Screen Analysis:** Real-time visual parsing of active windows for context-aware assistance.
    * **Optical Diagnostics:** Webcam integration for object recognition and environmental scanning.
* **Smart Ghost Mode:** An automated UI management system that transitions the interface into a stealth state during inactivity to optimize screen real estate.
* **Hardware Orchestration:** Direct kernel-level hooks for controlling System Audio, Display Brightness, and Instant OS Locking for security.

---

## 💻 Tech Stack

* **Architecture:** Modular Python 3.12+ 
* **Frontend Framework:** Futuristic HUD engineered with **PyQt6** and High-DPI support.
* **Large Language Models:** Llama 3.1 (Cloud API) & Llama 3 (Local Inference).
* **Neural TTS:** High-fidelity human-like speech synthesis via **Edge-TTS**.
* **Vision Engine:** OpenCV & PIL for sophisticated image processing.
* **System Automation:** Leverages `psutil`, `pywhatkit`, and `screen-brightness-control` for deep OS integration.

---

## 🛠️ Installation & Deployment

### 1. Repository Setup
```bash
git clone https://github.com/NSxSharpyy/Friday.git
cd Friday

```
### 2. Install Dependencies
Make sure you have Python 3.12+ installed. Open your terminal and run:
```bash
pip install -r requirements.txt

```

3. Setup AI Engines (Hybrid Brain)
The system is designed to work both online and offline. You can configure one or both:

Cloud Intelligence (Groq - High Speed):

Visit the Groq Console and generate a free API Key.

Launch the application and enter this key in the Secure Settings panel.

Benefit: Provides lightning-fast responses with zero load on your CPU.

Local Intelligence (Ollama - Private & Offline):

Download and install Ollama.


Open your terminal and run:
```bash
ollama run llama3.
```

Benefit: F.R.I.D.A.Y. will automatically fallback to this model if you lose internet connectivity, ensuring 100% privacy.

4. Launch F.R.I.D.A.Y.
Once the environment is ready, ignite the system with:
```
python my_friday.py
```
🎮 Command Center (Voice & Text)
You can interact with F.R.I.D.A.Y. using the following commands to verify its core modules:

⚡ 1. System Orchestration (OS Control)
Test how the AI interacts with your hardware:

"Good afternoon/morning/night" - Update about the time,temp,system info.

"Kaisi ho,Friday" - Response in your language.

"Lock the system" – Immediately locks the Windows workstation.

"Open [App Name]" – (e.g., "Open Notepad", "Open Chrome") Launches local applications.

"Set brightness to 70%" – Adjusts display levels using hardware hooks.

"What is my battery level?" – Reports current power status and charging state.

"Volume up / Volume down" – Controls system master audio.



🧠 2. Hybrid Brain (Cloud vs Local)
Switching between Groq (Online) and Ollama (Offline):

"Switch to Local mode" – Transitions processing to Ollama/Llama3.

"Search for [Topic]" – Fetches real-time information using Groq LPU.

"Write a Python script for..." – Tests the LLM's coding and logic capabilities.

👻 3. UI & Stealth Interaction
"Go to sleep" – Minimizes the HUD to the system tray (Ghost Mode).

"Wake up" – (Or use the Clap Trigger) Brings the futuristic UI back to full screen.

"Clear chat" – Wipes the current session's visual dialogue history.
