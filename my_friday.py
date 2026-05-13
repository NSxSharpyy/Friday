import sys
import os
import datetime
import time
import random
import asyncio
import ctypes
import psutil
import threading 
import speech_recognition as sr
import webbrowser
import re
import pywhatkit
import edge_tts
import pygame
import requests
import json
import platform
import base64
import pyttsx3 

# 🟢 MODULES FOR CLAP DETECTION 🟢
try:
    import sounddevice as sd
    import numpy as np
except ImportError:
    sd = None # APP CRASH NAHI HOGA AGAR MODULE MISSING HAI

# --- ADVANCED MODULES FOR VISION & EMAIL ---
try:
    import cv2
    from PIL import ImageGrab
    import win32com.client
except ImportError:
    pass

from groq import Groq 

try:
    import screen_brightness_control as sbc
except ImportError:
    sbc = None

os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_QPA_PLATFORM"] = "windows"

from PyQt6.QtWidgets import QApplication, QMainWindow, QLineEdit, QPushButton, QInputDialog, QMessageBox
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QObject

CONFIG_FILE = "friday_config.json"
MEMORY_FILE = "friday_memory.json"
PROTOCOL_FILE = "friday_protocols.json"

def load_json(filepath, default_data):
    if not os.path.exists(filepath):
        with open(filepath, 'w') as f: json.dump(default_data, f, indent=4)
        return default_data
    with open(filepath, 'r') as f: return json.load(f)

config = load_json(CONFIG_FILE, {"GROQ_API_KEY": ""})
memory = load_json(MEMORY_FILE, {"user_name": "Hansraj", "preferences": {}})
protocols = load_json(PROTOCOL_FILE, {"hacker_protocol": ["open cmd", "play hacker music"]})

if not os.path.exists("plugins"): os.makedirs("plugins")

pygame.mixer.init()

# 🟢 CLAP DETECTION BACKGROUND THREAD 🟢
class ClapDetector(QThread):
    clap_signal = pyqtSignal()
    
    def run(self):
        if not sd: return
        def audio_callback(indata, frames, time_info, status):
            volume_norm = np.linalg.norm(indata) * 10
            if volume_norm > 150: 
                self.clap_signal.emit()
                sd.sleep(2000) 
        try:
            with sd.InputStream(callback=audio_callback, channels=1, samplerate=44100):
                while True:
                    sd.sleep(1000)
        except Exception as e: pass

class FridaySignals(QObject):
    status = pyqtSignal(str)
    heard = pyqtSignal(str)
    action = pyqtSignal(str)
    response = pyqtSignal(str)
    log = pyqtSignal(str) 
    news = pyqtSignal(str)
    boot_done = pyqtSignal() 
    wake = pyqtSignal()   
    sleep = pyqtSignal()  
    update_hud_location = pyqtSignal(str, str) 

class FridayBackend(QThread):
    def __init__(self, api_key):
        super().__init__()
        self.signals = FridaySignals()
        self.is_speaking = False
        self.is_awake = True  
        self.client = Groq(api_key=api_key) if api_key else None
        self.location_data = {"city": "Unknown", "temp": "N/A"}
        self.last_interaction_time = time.time()

        self.voices = {
            "en": "en-GB-SoniaNeural", "hi": "hi-IN-SwaraNeural", "mr": "mr-IN-AarohiNeural",
            "es": "es-ES-ElviraNeural", "fr": "fr-FR-DeniseNeural", "ja": "ja-JP-NanamiNeural"
        }

    def fetch_geolocation(self):
        try:
            loc_res = requests.get("http://ip-api.com/json/", timeout=3).json()
            city = loc_res.get("city", "Unknown")
            weather_res = requests.get(f"https://wttr.in/{city}?format=%t", timeout=3).text
            temp = weather_res.strip()
            self.location_data = {"city": city.upper(), "temp": temp}
            self.signals.update_hud_location.emit(city.upper(), temp)
        except: pass

    def stop_speech(self):
        self.is_speaking = False
        if pygame.mixer.music.get_busy(): pygame.mixer.music.stop()

    # 🟢 FULLY INTEGRATED VOICE AUTO-DELETE 🟢
    def _play_audio_thread(self, filename):
        try:
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy() and self.is_speaking:
                pygame.time.Clock().tick(10)
        except: pass
        finally:
            self.is_speaking = False
            self.signals.status.emit("idle")
            
            try:
                pygame.mixer.music.stop()
                pygame.mixer.music.unload() 
            except: pass
            
            deleted = False
            attempts = 0
            while not deleted and attempts < 5:
                try:
                    time.sleep(0.5)
                    if os.path.exists(filename): 
                        os.remove(filename)
                    deleted = True
                except:
                    attempts += 1

    def speak(self, text, lang_code="en"):
        if not text: return
        self.stop_speech() 
        self.signals.response.emit(text) 
        clean_text = text.replace("*", "").replace("#", "").strip()
        self.signals.status.emit("speaking")
        self.is_speaking = True
        self.last_interaction_time = time.time()
        
        voice_id = self.voices.get(lang_code, "en-GB-SoniaNeural") 
        filename = f"voice_{random.randint(1, 99999)}.mp3"
        
        async def gen(): await edge_tts.Communicate(clean_text, voice_id).save(filename)
        
        try:
            asyncio.run(gen())
            threading.Thread(target=self._play_audio_thread, args=(filename,), daemon=True).start()
        except: 
            try:
                engine = pyttsx3.init()
                voices = engine.getProperty('voices')
                for voice in voices:
                    if "Zira" in voice.name or "female" in voice.name.lower():
                        engine.setProperty('voice', voice.id)
                        break
                engine.setProperty('rate', 170)
                engine.say(clean_text)
                engine.runAndWait()
            except: pass
            self.is_speaking = False
            self.signals.status.emit("idle")

    def cross_platform_lock(self):
        sys_os = platform.system()
        if sys_os == "Windows": os.system("rundll32.exe user32.dll,LockWorkStation")
        elif sys_os == "Darwin": os.system("pmset displaysleepnow") 
        elif sys_os == "Linux": os.system("xdg-screensaver lock")

    def analyze_image_with_groq(self, image_path, prompt):
        try:
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            chat = self.client.chat.completions.create(
                model="llama-3.2-11b-vision-preview",
                messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_string}"}}]}]
            )
            self.speak(chat.choices[0].message.content.strip(), "en")
        except Exception as e:
            self.speak("Vision link failed. Ensure your Groq API key supports Vision models.", "en")

    def execute_command(self, query):
        self.last_interaction_time = time.time()
        query = query.lower().strip()
        user_name = memory.get("user_name", "Hansraj")

        for proto_name, actions in protocols.items():
            if proto_name.replace("_", " ") in query:
                self.speak(f"Initiating {proto_name.replace('_', ' ')}.", "en")
                for action in actions: self.execute_command(action)
                return

        if "news in" in query or "what happened in" in query or "news about" in query:
            self.signals.action.emit("FETCHING LOCATION NEWS")
            
            if "in" in query: location = query.split("in")[-1].strip()
            elif "about" in query: location = query.split("about")[-1].strip()
            else: location = "the world"
            
            self.speak(f"Fetching intelligence feed for {location.upper()}...", "en")
            
            prompt = f"Give me a short 2-sentence breaking news update or current event about '{location}'. You MUST start your response with the exact tag [news]."
            try:
                chat = self.client.chat.completions.create(
                    messages=[{"role": "system", "content": "You are Friday. Be concise."}, {"role": "user", "content": prompt}],
                    model="llama-3.1-8b-instant", temperature=0.7, max_tokens=150, timeout=8
                )
                reply = chat.choices[0].message.content.strip()
                if reply.lower().startswith("[news]"):
                    clean_reply = reply[6:].strip()
                    self.signals.news.emit(clean_reply) 
                    self.speak(clean_reply, "en")       
                else:
                    self.signals.news.emit(reply)
                    self.speak(reply, "en")
            except Exception as e:
                self.speak(f"Unable to fetch news for {location} right now.", "en")
            return

        if "standby" in query or "hide yourself" in query or "go to background" in query:
            self.is_awake = False
            self.signals.sleep.emit()
            self.speak("Going to standby mode. Clap or call my name if you need me.", "en")
            return

        greetings = ["good morning", "good afternoon", "good evening", "routine"]
        if any(greet in query for greet in greetings) and "news" not in query:
            t_str = datetime.datetime.now().strftime("%I:%M %p")
            city = self.location_data['city']
            temp = self.location_data['temp']
            report = f"Greetings {user_name}. The time is {t_str}. You are currently in {city}, temperature is {temp}. Systems are green."
            self.signals.action.emit("LOCAL ROUTINE EXECUTED"); self.speak(report, "en")
            return

        elif "lock pc" in query or "lock system" in query:
            self.signals.action.emit("LOCKING PC")
            self.speak(f"Locking the system, {user_name}.", "en"); self.cross_platform_lock()
            return

        elif "volume" in query:
            if "up" in query or "increase" in query:
                for _ in range(5): ctypes.windll.user32.keybd_event(0xAF, 0, 0, 0)
                self.signals.action.emit("VOLUME UP"); self.speak("Volume increased.", "en")
            else:
                for _ in range(5): ctypes.windll.user32.keybd_event(0xAE, 0, 0, 0)
                self.signals.action.emit("VOLUME DOWN"); self.speak("Volume decreased.", "en")
            return

        elif "brightness" in query:
            if sbc:
                val = 80 if "up" in query or "increase" in query else 20
                sbc.set_brightness(val)
                self.signals.action.emit("BRIGHTNESS UPDATED"); self.speak("Brightness adjusted.", "en")
            return

        elif query.startswith("open "):
            target = query.replace("open ", "").strip()
            self.signals.action.emit(f"Opening {target.upper()}")
            app_map = {"notepad": "notepad", "cmd": "cmd"}
            web_apps = ["youtube", "google", "github", "whatsapp"]
            
            if target in app_map: os.system(f"start {app_map[target]}")
            elif any(domain in target for domain in web_apps) or "." in target: 
                webbrowser.open(f"https://www.{target}.com" if "." not in target else f"https://{target}")
            else: os.system(f"start {target}")
            self.speak(f"Opening {target}.", "en"); return

        elif query.startswith("play "):
            song = query.replace("play ", "").strip()
            self.signals.action.emit(f"Youtube: {song.upper()}")
            self.speak(f"Playing {song}.", "en"); pywhatkit.playonyt(song)
            return

        elif "scan screen" in query:
            self.signals.action.emit("SCREEN SCAN")
            try:
                self.speak("Capturing screen...", "en")
                screenshot = ImageGrab.grab()
                screenshot.save("temp_screen.jpg")
                self.analyze_image_with_groq("temp_screen.jpg", "Analyze this screen and tell me what is going on briefly.")
            except Exception as e: self.speak("Screen capture failed.", "en")
            return

        elif "use camera" in query:
            self.signals.action.emit("CAMERA SCAN")
            try:
                self.speak("Accessing webcam...", "en")
                cap = cv2.VideoCapture(0)
                ret, frame = cap.read()
                if ret:
                    cv2.imwrite("temp_cam.jpg", frame)
                    cap.release()
                    self.analyze_image_with_groq("temp_cam.jpg", "Describe what you see in this picture.")
                else: self.speak("Failed to read from webcam.", "en")
            except Exception as e: self.speak("Camera offline.", "en")
            return

        elif "read email" in query:
            self.signals.action.emit("FETCHING EMAIL")
            try:
                outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
                inbox = outlook.GetDefaultFolder(6) 
                messages = inbox.Items
                messages.Sort("[ReceivedTime]", True)
                last_msg = messages.GetFirst()
                self.speak(f"Your last email is from {last_msg.SenderName} regarding {last_msg.Subject}.", "en")
            except Exception as e:
                self.speak("Microsoft Outlook is not configured on this machine.", "en")
            return

        elif "ollama test" in query:
            self.signals.action.emit("LOCAL OLLAMA FALLBACK")
            try:
                self.speak("Testing local offline brain...", "en")
                res = requests.post("http://localhost:11434/api/generate", json={"model": "llama3", "prompt": "Say exactly: 'Ollama local connection successful.'", "stream": False}, timeout=30)
                if "error" in res.json():
                    self.speak(f"Local Brain Error: {res.json()['error']}", "en")
                else:
                    local_reply = res.json().get("response", "No response received.")
                    self.speak(local_reply, "en")
            except Exception as e:
                self.speak("Local Ollama Brain is fully offline.", "en")
            return
        
        else:
            if not self.client:
                self.speak("Neural Link disconnected. Please set your API key in Settings.", "en"); return
            self.signals.action.emit("AI NEURAL QUERY")
            
            try:
                system_prompt = f"You are F.R.I.D.A.Y. The user's name is {user_name}. RULE 1: Reply natively. RULE 2: Start with lang code e.g., [en], [hi]. For news use [news]. Keep it concise."
                chat = self.client.chat.completions.create(
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": query}],
                    model="llama-3.1-8b-instant", temperature=0.7, max_tokens=200,
                    timeout=8 
                )
                reply = chat.choices[0].message.content.strip()
                detected_lang, is_news = "en", False
                match_lang = re.match(r"\[([a-z]{2})\]", reply, re.IGNORECASE)
                if match_lang: detected_lang = match_lang.group(1).lower(); reply = reply[match_lang.end():].strip() 
                if reply.lower().startswith("[news]"): is_news = True; reply = reply[6:].strip() 
                
                self.speak(reply, detected_lang)
                if is_news: self.signals.news.emit(reply)
                
            except Exception as e: 
                self.signals.log.emit(f"⚠️ API Error / Timeout: {str(e)}")
                self.signals.action.emit("LOCAL OLLAMA FALLBACK")
                try:
                    res = requests.post("http://localhost:11434/api/generate", json={"model": "llama3", "prompt": query, "stream": False}, timeout=30)
                    if "error" in res.json():
                        self.speak(f"Local Brain Error: {res.json()['error']}", "en")
                    else:
                        local_reply = res.json().get("response", "I am unable to think locally right now.")
                        self.speak(local_reply, "en")
                except:
                    self.speak("Both Cloud Neural Link and Local Ollama Brain are offline.", "en")

    def run(self):
        self.fetch_geolocation()
        user_name = memory.get('user_name', 'Hansraj')
        boot_dialogue = (
            "Importing preferences and calibrating virtual environment. "
            "Doing a check on virtual neural networks. "
            "All systems are fully operational. "
            f"Welcome back, {user_name}."
        )
        self.speak(boot_dialogue, "en")
        
        time.sleep(1); 
        while self.is_speaking: time.sleep(0.1)
        self.signals.boot_done.emit()
        
        r = sr.Recognizer(); r.pause_threshold = 0.6; r.energy_threshold = 300 
        
        while True:
            if self.is_awake and (time.time() - self.last_interaction_time > 45) and not self.is_speaking:
                self.is_awake = False; self.signals.sleep.emit() 
            try:
                with sr.Microphone() as source:
                    if not self.is_speaking: self.signals.status.emit("idle")
                    r.adjust_for_ambient_noise(source, duration=0.5)
                    audio = r.listen(source, timeout=None, phrase_time_limit=8)
                if not self.is_speaking: self.signals.status.emit("listening")
                query = r.recognize_google(audio, language='en-in').lower()
                
                if self.is_speaking and any(w in query for w in ["friday", "stop"]): self.stop_speech()
                
                if "friday" in query:
                    self.last_interaction_time = time.time()
                    if not self.is_awake: self.is_awake = True; self.signals.wake.emit() 
                    query = query.replace("friday", "").strip()
                    self.signals.heard.emit("FRIDAY " + query) 
                    if query: 
                        self.execute_command(query)
                    else: 
                        self.speak("Online and ready.", "en")
                elif self.is_awake and query:
                    self.last_interaction_time = time.time()
                    self.signals.heard.emit(query)
                    self.execute_command(query)
            except: time.sleep(0.5)

HTML_UI = """
<!DOCTYPE html>
<html>
<head>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap');
        body { margin: 0; overflow: hidden; background-color: #00050a; font-family: 'Orbitron', sans-serif; color: #00d4ff; display: flex; justify-content: center; align-items: center; height: 100vh; width: 100vw; }
        #boot-screen { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #00050a; z-index: 9999; display: flex; flex-direction: column; justify-content: center; align-items: center; transition: opacity 1.5s ease-in-out; }
        .boot-ring { position: absolute; border-radius: 50%; }
        .ring-large { width: 500px; height: 500px; border: 2px dashed rgba(0,212,255,0.3); animation: spin 10s linear infinite; }
        .ring-med { width: 400px; height: 400px; border: 5px solid transparent; border-left: 5px solid #00d4ff; border-right: 5px solid #00d4ff; animation: spin-rev 5s linear infinite; }
        .ring-small { width: 300px; height: 300px; border: 3px solid rgba(0,255,157,0.5); border-top: 3px solid transparent; border-bottom: 3px solid transparent; animation: spin 3s linear infinite; }
        .boot-text { font-size: 40px; font-weight: bold; letter-spacing: 15px; color: #00d4ff; text-shadow: 0 0 20px #00d4ff; animation: pulse 2s infinite; z-index: 100; }
        .boot-subtext { position: absolute; margin-top: 550px; font-size: 12px; color: #00ff9d; letter-spacing: 5px; animation: blink 1.5s infinite; }
        .holo-pulse { position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 900; background: radial-gradient(circle at center, transparent 40%, rgba(0, 212, 255, 0.15) 100%); animation: screen-pulse 4s ease-in-out infinite; }
        @keyframes screen-pulse { 0%, 100% { opacity: 0.3; box-shadow: inset 0 0 50px rgba(0, 212, 255, 0.2); } 50% { opacity: 1; box-shadow: inset 0 0 150px rgba(0, 212, 255, 0.4); } }
        
        .top-left-panel { position: absolute; left: 50px; top: 50px; width: 250px; border-left: 5px solid #00ff9d; padding: 15px; background: rgba(0, 15, 30, 0.5); backdrop-filter: blur(10px); clip-path: polygon(0 0, 100% 0, 100% calc(100% - 15px), calc(100% - 15px) 100%, 0 100%); z-index: 1;}
        .tl-title { font-size: 14px; font-weight: bold; color: #00ff9d; letter-spacing: 2px; margin-bottom: 15px; text-shadow: 0 0 10px #00ff9d;}
        .data-row { font-size: 10px; margin-bottom: 8px; display: flex; justify-content: space-between; border-bottom: 1px dashed rgba(0,212,255,0.2); padding-bottom: 4px;}
        .radar-box { width: 100%; height: 60px; border: 1px solid rgba(0, 212, 255, 0.3); margin-top: 15px; position: relative; overflow: hidden; background: rgba(0, 212, 255, 0.05); }
        .radar-line { position: absolute; left: 0; width: 2px; height: 100%; background: #00ff9d; box-shadow: 0 0 15px #00ff9d; animation: scan 2s linear infinite; }
        .blip-1 { position: absolute; top: 30%; left: 40%; width: 5px; height: 5px; background: #ff9d00; border-radius: 50%; box-shadow: 0 0 8px #ff9d00; animation: blink 2s infinite; }
        .blip-2 { position: absolute; top: 60%; left: 70%; width: 5px; height: 5px; background: #00d4ff; border-radius: 50%; box-shadow: 0 0 8px #00d4ff; animation: blink 3s infinite; }
        
        .feature-panel { position: absolute; left: 50px; top: 250px; width: 250px; border-left: 5px solid #ff2d00; background: rgba(0, 15, 30, 0.5); padding: 15px; padding-right: 5px; backdrop-filter: blur(10px); clip-path: polygon(0 0, 100% 0, 100% calc(100% - 15px), calc(100% - 15px) 100%, 0 100%); z-index: 100; }
        .feature-title { font-size: 12px; font-weight: bold; color: #ff2d00; margin-bottom: 10px; border-bottom: 1px dashed rgba(255,45,0,0.3); padding-bottom: 5px; letter-spacing: 1px; padding-right: 10px;}
        .feature-list { max-height: 220px; overflow-y: auto; padding-right: 10px; }
        .feature-list::-webkit-scrollbar { width: 4px; }
        .feature-list::-webkit-scrollbar-track { background: rgba(0,0,0,0.2); border-radius: 2px;}
        .feature-list::-webkit-scrollbar-thumb { background: #ff2d00; border-radius: 2px; box-shadow: 0 0 5px #ff2d00;}
        .feature-btn { display: block; width: 100%; background: rgba(255, 45, 0, 0.1); border: 1px solid rgba(255, 45, 0, 0.3); color: #fff; padding: 10px; margin-bottom: 8px; font-family: 'Orbitron', sans-serif; font-size: 10px; text-align: left; cursor: pointer; transition: 0.3s; text-transform: uppercase; letter-spacing: 1px;}
        .feature-btn:hover { background: rgba(255, 45, 0, 0.4); box-shadow: 0 0 15px #ff2d00; transform: translateX(5px); border-left: 3px solid #fff; }

        .news-panel { position: absolute; left: 50px; bottom: 150px; width: 250px; border-left: 5px solid #00d4ff; background: rgba(0, 15, 30, 0.5); padding: 15px; backdrop-filter: blur(10px); clip-path: polygon(0 0, 100% 0, 100% calc(100% - 15px), calc(100% - 15px) 100%, 0 100%); opacity: 0; transition: opacity 0.5s ease-in-out; z-index: 100;}
        .news-title { font-size: 12px; font-weight: bold; color: #00d4ff; margin-bottom: 10px; border-bottom: 1px dashed rgba(0,212,255,0.3); padding-bottom: 5px; letter-spacing: 1px;}
        .news-content { font-size: 10px; color: #fff; line-height: 1.5; max-height: 200px; overflow-y: hidden; text-transform: uppercase;}
        
        .reactor-container { position: relative; width: 550px; height: 550px; display: flex; justify-content: center; align-items: center; z-index: 1;}
        .ring { position: absolute; border-radius: 50%; box-sizing: border-box; transition: all 0.5s ease;}
        .ring-1 { width: 520px; height: 520px; border: 1px dashed rgba(0, 212, 255, 0.2); animation: spin 40s linear infinite; }
        .ring-2 { width: 490px; height: 490px; border: 5px solid transparent; border-left: 5px solid #00d4ff; border-right: 5px solid #00d4ff; animation: spin-rev 15s linear infinite; filter: drop-shadow(0 0 15px #00d4ff); }
        .core { width: 170px; height: 170px; border-radius: 50%; border: 4px solid #00d4ff; background: radial-gradient(circle, rgba(0, 212, 255, 0.2) 0%, #00050a 80%); box-shadow: 0 0 60px rgba(0, 212, 255, 0.5); display: flex; justify-content: center; align-items: center; font-size: 18px; font-weight: bold; letter-spacing: 4px; text-shadow: 0 0 10px #00d4ff; z-index: 10; transition: all 0.4s ease-in-out;}
        .notif-box { position: absolute; right: 280px; top: 50px; width: 40px; height: 40px; border: 2px solid #ff9d00; border-radius: 8px; display:flex; justify-content:center; align-items:center; background: rgba(255, 157, 0, 0.1); box-shadow: 0 0 10px rgba(255,157,0,0.3); z-index: 1;}
        .notif-icon-text { font-size: 20px; font-weight: bold; color: #ff9d00; text-shadow: 0 0 5px #ff9d00; }
        .notif-badge { position: absolute; top: -5px; right: -5px; width: 12px; height: 12px; background: #ff2d00; border-radius: 50%; box-shadow: 0 0 8px #ff2d00; animation: blink 1.5s infinite; }
        
        .top-right-info { position: absolute; right: 50px; top: 50px; text-align: right; z-index: 1;}
        .temp-dial-container { position: absolute; right: 50px; top: 130px; z-index: 1;}
        
        .action-panel { position: absolute; right: 50px; top: 260px; width: 300px; height: 400px; border-right: 5px solid #ff9d00; background: rgba(0, 15, 30, 0.5); padding: 10px; overflow: hidden; clip-path: polygon(15px 0, 100% 0, 100% 100%, 0 100%, 0 15px); z-index: 1;}
        .log-box { display: flex; flex-direction: column-reverse; height: calc(100% - 30px); overflow-y: auto; font-family: monospace; font-size: 10px; color: #aaa; }
        .log-line { margin-bottom: 6px; padding-left: 8px; border-left: 2px solid transparent; animation: slideIn 0.3s ease-out; }
        @keyframes scan { 0% { left: 0; } 50% { left: 100%; } 100% { left: 0; } }
        @keyframes slideIn { from { transform: translateX(20px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        .cmd-frame { position: absolute; bottom: 80px; left: 50%; transform: translateX(-50%); width: 550px; padding: 10px; border: 2px solid rgba(0,212,255,0.4); border-left: 6px solid #00d4ff; background: rgba(0, 15, 30, 0.7); clip-path: polygon(15px 0, 100% 0, 100% 100%, 0 100%, 0 15px); z-index: 1;}
        .cmd-label { font-size: 12px; font-weight: bold; margin-bottom: 25px; text-align:center; color: #00ff9d; letter-spacing: 2px;}
        .bottom-dials { position: absolute; bottom: 50px; left: 50px; display: flex; gap: 20px; z-index: 1;}
        .dial { width: 90px; height: 90px; border-radius: 50%; border: 3px solid rgba(0, 212, 255, 0.2); display: flex; justify-content: center; align-items: center; text-align: center; position:relative;}
        .dial-ring { position:absolute; width: 100px; height: 100px; border: 2px dashed rgba(0, 212, 255, 0.4); border-radius: 50%; animation: spin 10s linear infinite;}
        .dial-label { font-size: 9px; font-weight: bold; color: #aaa;}
        .dial-val { font-size: 20px; font-weight: bold; color: #fff;}
        @keyframes spin { 100% { transform: rotate(360deg); } }
        @keyframes spin-rev { 100% { transform: rotate(-360deg); } }
        @keyframes blink { 50% { opacity: 0.3; } }
        @keyframes pulse { 0%, 100% { opacity: 0.7; transform: scale(0.98); } 50% { opacity: 1; transform: scale(1.02); } }
    </style>
</head>
<body>
    <div id="boot-screen">
        <div class="boot-ring ring-large"></div>
        <div class="boot-ring ring-med"></div>
        <div class="boot-ring ring-small"></div>
        <div class="boot-text">F.R.I.D.A.Y.</div>
        <div class="boot-subtext">GLOBAL UPLINK INITIALIZED...</div>
    </div>
    <div class="holo-pulse"></div>
    <div class="top-left-panel">
        <div class="tl-title">SYSTEM DIAGNOSTICS</div>
        <div class="data-row"><span>CONNECTION:</span> <span style="color:#00ff9d;">SECURE</span></div>
        <div class="data-row"><span>LATENCY:</span> <span>12ms</span></div>
        <div class="data-row"><span>ENCRYPTION:</span> <span>AES-256</span></div>
        <div class="radar-box"><div class="radar-line"></div><div class="blip-1"></div><div class="blip-2"></div></div>
    </div>
    
    <div class="feature-panel">
        <div class="feature-title">ALL COMMANDS MENU</div>
        <div class="feature-list">
            <button class="feature-btn" onclick="executeFeature('routine')">> RUN DIAGNOSTICS</button>
            <button class="feature-btn" onclick="executeFeature('scan screen')" style="border-color:#00d4ff; color:#00d4ff;">> SCAN SCREEN (VISION)</button>
            <button class="feature-btn" onclick="executeFeature('use camera')" style="border-color:#00d4ff; color:#00d4ff;">> ACCESS CAMERA (VISION)</button>
            <button class="feature-btn" onclick="executeFeature('read email')" style="border-color:#ff9d00; color:#ff9d00;">> READ LATEST EMAIL</button>
            <button class="feature-btn" onclick="executeFeature('ollama test')" style="border-color:#00ff9d; color:#00ff9d;">> OFFLINE AI (OLLAMA)</button>
            <button class="feature-btn" onclick="executeFeature('news')">> FETCH LATEST NEWS</button>
            <button class="feature-btn" onclick="executeFeature('lock pc')">> SECURE SYSTEM (LOCK)</button>
            <button class="feature-btn" onclick="executeFeature('standby')">> STANDBY MODE (HIDE)</button>
            <button class="feature-btn" onclick="executeFeature('volume up')">> INCREASE VOLUME</button>
            <button class="feature-btn" onclick="executeFeature('volume down')">> DECREASE VOLUME</button>
            <button class="feature-btn" onclick="executeFeature('brightness up')">> INCREASE BRIGHTNESS</button>
            <button class="feature-btn" onclick="executeFeature('brightness down')">> DECREASE BRIGHTNESS</button>
            <button class="feature-btn" onclick="executeFeature('play believer')">> PLAY MUSIC</button>
            <button class="feature-btn" onclick="executeFeature('open youtube')">> LAUNCH YOUTUBE</button>
            <button class="feature-btn" onclick="executeFeature('open github')">> LAUNCH GITHUB</button>
            <button class="feature-btn" onclick="executeFeature('open whatsapp')">> OPEN WHATSAPP</button>
            <button class="feature-btn" onclick="executeFeature('open cmd')">> LAUNCH TERMINAL</button>
            <button class="feature-btn" onclick="executeFeature('hacker protocol')">> HACKER PROTOCOL</button>
        </div>
    </div>

    <div class="news-panel" id="news-panel">
        <div class="news-title">LIVE INTELLIGENCE FEED</div>
        <div class="news-content" id="news-content">Awaiting uplink...</div>
    </div>
    <div class="cmd-frame"><div class="cmd-label">COMMAND OVERRIDE</div></div>
    <div class="reactor-container"><div class="ring ring-1"></div><div class="ring ring-2"></div><div class="core" id="status-core">INIT</div></div>
    <div class="bottom-dials">
        <div class="dial"><div class="dial-ring"></div><div class="dial-inner"><div class="dial-val" id="ram-dial">80%</div><div class="dial-label">MEM</div></div></div>
        <div class="dial"><div class="dial-ring" style="animation-direction: reverse;"></div><div class="dial-inner"><div class="dial-val" id="cpu-dial" style="color:#ff9d00;">53%</div><div class="dial-label">CPU</div></div></div>
    </div>
    <div class="notif-box"><div class="notif-icon-text">!</div><div class="notif-badge"></div></div>
    
    <div class="top-right-info"><div id="live-clock" style="font-size:28px; font-weight:bold; text-shadow:0 0 10px #00d4ff;">00:00:00</div><div id="hud-location" style="font-size:10px; color:#aaa;">UPLINKING LOCATION...</div></div>
    <div class="temp-dial-container">
        <div class="dial" style="border-color: rgba(255, 157, 0, 0.4);">
            <div class="dial-ring" style="border-color: rgba(255, 157, 0, 0.5); animation-duration: 15s;"></div>
            <div class="dial-inner"><div class="dial-val" id="hud-temp" style="color:#ff9d00; text-shadow: 0 0 5px #ff9d00;">--</div><div class="dial-label">TEMP</div></div>
        </div>
    </div>
    
    <div class="action-panel">
        <div style="font-size:10px; font-weight:bold; color:#ff9d00; border-bottom:1px solid rgba(255,157,0,0.3); padding-bottom:5px; margin-bottom:10px;">ACTION TERMINAL</div>
        <div class="log-box" id="activity-log"></div>
    </div>
    
    <script>
        setInterval(() => { document.getElementById('live-clock').innerText = new Date().toLocaleTimeString('en-US', {hour12:false}); }, 1000);
        
        function executeFeature(cmd) {
            document.title = "EXEC:" + cmd;
            setTimeout(() => { document.title = "FRIDAY HUD"; }, 100);
        }

        function updateUI(cpu, ram, status) {
            document.getElementById('ram-dial').innerText = ram + '%';
            document.getElementById('cpu-dial').innerText = cpu + '%';
            let core = document.getElementById('status-core');
            core.innerText = status.toUpperCase();
            if(status === 'speaking') { core.style.boxShadow = "0 0 100px #ff2d00"; core.style.borderColor = "#ff2d00"; }
            else if(status === 'listening') { core.style.boxShadow = "0 0 100px #00ff9d"; core.style.borderColor = "#00ff9d"; }
            else { core.style.boxShadow = "0 0 50px rgba(0, 212, 255, 0.6)"; core.style.borderColor = "#00d4ff"; }
        }
        function updateLocation(city, temp) {
            document.getElementById('hud-location').innerText = city;
            document.getElementById('hud-temp').innerText = temp;
        }
        function addLog(type, msg) {
            let logBox = document.getElementById('activity-log');
            if(!logBox) return;
            let div = document.createElement('div');
            div.className = 'log-line';
            if(type === 'heard') { div.style.borderColor = '#00ff9d'; div.style.color = '#00ff9d'; div.innerText = "> Heard: " + msg.toUpperCase(); }
            else if(type === 'action') { div.style.borderColor = '#aaa'; div.innerText = "> Action: " + msg.toUpperCase(); }
            else if(type === 'speaking') { div.style.borderColor = '#ff2d00'; div.style.color = '#ff2d00'; div.innerText = "> Reply: " + msg; }
            else { div.style.borderColor = '#00d4ff'; div.innerText = "> " + msg.toUpperCase(); }
            logBox.prepend(div); 
            if (logBox.childNodes.length > 15) logBox.removeChild(logBox.lastChild);
        }
        function showNews(text) {
            let panel = document.getElementById('news-panel');
            let content = document.getElementById('news-content');
            content.innerText = text;
            panel.style.opacity = 1;
            setTimeout(() => { panel.style.opacity = 0; }, 20000); 
        }
        function hideBootScreen() {
            let bootScreen = document.getElementById('boot-screen');
            bootScreen.style.opacity = '0';
            setTimeout(() => { bootScreen.style.display = 'none'; }, 1500);
        }
    </script>
</body>
</html>
"""

class FridayUltimateHUD(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.browser = QWebEngineView()
        self.browser.setHtml(HTML_UI)
        self.setCentralWidget(self.browser)
        
        self.browser.titleChanged.connect(self.handle_html_clicks)

        self.btn_shutdown = QPushButton("SHUTDOWN", self)
        self.btn_shutdown.setStyleSheet("background: rgba(255, 0, 0, 0.1); color: #ff2d00; border: 2px solid #ff2d00; border-radius: 5px; font-family: Orbitron; font-weight: bold; font-size: 14px; padding: 10px;")
        self.btn_shutdown.clicked.connect(self.shutdown_friday_only)

        self.btn_minimize = QPushButton("MINIMIZE", self)
        self.btn_minimize.setStyleSheet("background: rgba(255, 157, 0, 0.1); color: #ff9d00; border: 2px solid #ff9d00; border-radius: 5px; font-family: Orbitron; font-weight: bold; font-size: 14px; padding: 10px;")
        self.btn_minimize.clicked.connect(self.minimize_ui)

        self.btn_settings = QPushButton("⚙️ SETTINGS", self)
        self.btn_settings.setStyleSheet("background: rgba(0, 212, 255, 0.1); color: #00d4ff; border: 2px solid #00d4ff; border-radius: 5px; font-family: Orbitron; font-weight: bold; font-size: 14px; padding: 10px;")
        self.btn_settings.clicked.connect(self.open_settings)

        self.cmd_input = QLineEdit(self)
        self.cmd_input.setPlaceholderText("> COMMAND OVERRIDE...")
        self.cmd_input.setStyleSheet("background: transparent; color: #00ff9d; border: none; font-family: Orbitron; font-size: 16px; padding: 10px; font-weight: bold;")
        self.cmd_input.returnPressed.connect(self.process_text_command)

        self.current_status = "init"
        self.ui_loaded = False
        self.browser.loadFinished.connect(self.on_ui_loaded)
        self.timer = QTimer(); self.timer.timeout.connect(self.update_telemetry)

        api_key = config.get("GROQ_API_KEY", "")
        self.backend = FridayBackend(api_key)
        self.backend.signals.status.connect(self.update_status)
        self.backend.signals.heard.connect(self.update_log_heard)
        self.backend.signals.action.connect(self.update_log_action)
        self.backend.signals.response.connect(self.update_log_speaking)
        self.backend.signals.news.connect(self.update_news_panel)
        self.backend.signals.boot_done.connect(self.hide_startup_animation)
        self.backend.signals.update_hud_location.connect(self.update_hud_loc)
        self.backend.signals.wake.connect(self.wake_up)
        self.backend.signals.sleep.connect(self.sleep_ui)
        
        self.clap_detector = ClapDetector()
        self.clap_detector.clap_signal.connect(self.on_clap_detected)
        self.clap_detector.start()
        
        self.backend.start()
        self.showFullScreen()

    def minimize_ui(self):
        self.backend.is_awake = False
        self.showMinimized() 

    def on_clap_detected(self):
        if not self.backend.is_awake:
            self.backend.is_awake = True
            self.backend.last_interaction_time = time.time()
            self.wake_up()
            if self.ui_loaded: self.browser.page().runJavaScript("addLog('action', 'ACOUSTIC ANOMALY DETECTED: WAKING UP');")
            self.backend.speak("At your service, Boss.", "en")

    def handle_html_clicks(self, title):
        if title.startswith("EXEC:"):
            cmd = title.split("EXEC:")[1]
            self.backend.is_awake = True
            self.backend.last_interaction_time = time.time()
            if self.ui_loaded: 
                clean_cmd = str(cmd).replace("'", "\\'").replace('"', '\\"')
                self.browser.page().runJavaScript(f"addLog('generic', 'UI Click: {clean_cmd.upper()}');")
            threading.Thread(target=self.backend.execute_command, args=(cmd,), daemon=True).start()

    def on_ui_loaded(self, ok):
        if ok: self.ui_loaded = True; self.timer.start(1000)

    def open_settings(self):
        key, ok = QInputDialog.getText(self, 'F.R.I.D.A.Y. Protocol', 'Enter GROQ API Key to establish Neural Link:')
        if ok and key:
            config["GROQ_API_KEY"] = key
            with open(CONFIG_FILE, 'w') as f: json.dump(config, f)
            self.backend.client = Groq(api_key=key)
            QMessageBox.information(self, "Neural Link", "API Key Saved Successfully. Neural Link Online.")

    def hide_startup_animation(self):
        if self.ui_loaded: self.browser.page().runJavaScript("hideBootScreen(); addLog('action', 'System fully operational.');")

    def resizeEvent(self, event):
        center_x = self.width() // 2
        self.btn_shutdown.setGeometry(center_x - 240, 20, 150, 45)
        self.btn_minimize.setGeometry(center_x - 75, 20, 150, 45)
        self.btn_settings.setGeometry(center_x + 90, 20, 150, 45)
        self.cmd_input.setGeometry((self.width() - 500) // 2, self.height() - 110, 500, 45)
        super().resizeEvent(event)

    def process_text_command(self):
        cmd = self.cmd_input.text().lower().strip(); self.cmd_input.clear()
        if cmd: 
            self.backend.is_awake = True
            self.backend.last_interaction_time = time.time()
            if self.ui_loaded: 
                clean_cmd = str(cmd).replace("'", "\\'").replace('"', '\\"')
                self.browser.page().runJavaScript(f"addLog('generic', 'Command: {clean_cmd}');")
            threading.Thread(target=self.backend.execute_command, args=(cmd,), daemon=True).start()

    def shutdown_friday_only(self):
        self.backend.stop_speech(); sys.exit() 

    def update_telemetry(self):
        if self.ui_loaded:
            cpu, ram = psutil.cpu_percent(), psutil.virtual_memory().percent
            self.browser.page().runJavaScript(f"updateUI({cpu}, {ram}, '{self.current_status}');")

    def update_hud_loc(self, city, temp):
        if self.ui_loaded: 
            clean_city = str(city).replace("'", "\\'")
            self.browser.page().runJavaScript(f"updateLocation('{clean_city}', '{temp}');")

    def update_status(self, s): self.current_status = s; self.update_telemetry() 
    
    def update_log_heard(self, msg): 
        if self.ui_loaded: 
            clean_m = str(msg).replace("'", "\\'").replace('"', '\\"').replace("\n", " ")
            self.browser.page().runJavaScript(f"addLog('heard', '{clean_m}');")
            
    def update_log_action(self, msg): 
        if self.ui_loaded: 
            clean_m = str(msg).replace("'", "\\'").replace('"', '\\"').replace("\n", " ")
            self.browser.page().runJavaScript(f"addLog('action', '{clean_m}');")
            
    def update_log_speaking(self, msg): 
        if self.ui_loaded: 
            clean_m = str(msg).replace("'", "\\'").replace('"', '\\"').replace("\n", " ")
            self.browser.page().runJavaScript(f"addLog('speaking', '{clean_m}');")
        
    def update_news_panel(self, m):
        if self.ui_loaded:
            clean_m = str(m).replace("'", "\\'").replace('"', '\\"').replace("\n", " ")
            self.browser.page().runJavaScript(f"showNews('{clean_m}');")

    def wake_up(self): 
        self.showNormal() 
        self.showFullScreen()
        self.activateWindow()
        
    def sleep_ui(self): self.hide()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    hud = FridayUltimateHUD()
    sys.exit(app.exec())