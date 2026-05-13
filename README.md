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
git clone [https://github.com/NSxSharpyy/Friday.git](https://github.com/NSxSharpyy/Friday.git)
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
```

Open your terminal and run:
```bash
ollama run llama3.
```

Benefit: F.R.I.D.A.Y. will automatically fallback to this model if you lose internet connectivity, ensuring 100% privacy.
```
```
4. Launch F.R.I.D.A.Y.
Once the environment is ready, ignite the system with:
```
python my_friday.py
