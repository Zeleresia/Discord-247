import json
import time
import requests
import websocket
import psutil
import threading
from pathlib import Path
from .config import load_config, save_config

API = "https://discord.com/api/v9"
GATEWAY_URL = "wss://gateway.discord.gg/?v=9&encoding=json"

class DiscordBot:
    def __init__(self, token: str, config_path: Path):
        self.token = token
        self.headers = {"Authorization": token, "Content-Type": "application/json"}
        self.config_path = config_path
        self.config = load_config(config_path)
        self.userinfo = None
        self.username = ""
        self.discriminator = ""
        self.userid = ""
        self.monitoring_active = True
        self.session_connected = False
        self.voice_connected = False
        self.start_time = time.time()
        self._presence_thread = None
        self.ws = None
        self.heartbeat_thread = None
        self.sequence = None
        self.session_id = None

    @staticmethod
    def validate_token(token: str, timeout=10) -> bool:
        if not token:
            return False
        try:
            r = requests.get(f"{API}/users/@me", headers={"Authorization": token, "Content-Type": "application/json"}, timeout=timeout)
            return r.status_code == 200
        except Exception:
            return False

    def connect(self, timeout=10) -> None:
        r = requests.get(f"{API}/users/@me", headers=self.headers, timeout=timeout)
        if r.status_code != 200:
            raise RuntimeError("Failed to get user info")
        self.userinfo = r.json()
        self.username = self.userinfo.get("username", "")
        self.discriminator = self.userinfo.get("discriminator", "")
        self.userid = self.userinfo.get("id", "")

    def get_system_stats(self) -> dict:
        p = psutil.Process()
        mem_mb = int(p.memory_info().rss / 1024 / 1024)
        cpu = int(p.cpu_percent(interval=0.1))
        
        uptime = time.strftime("%H:%M:%S", time.gmtime(time.time() - self.start_time))
        return {"memory_mb": mem_mb, "cpu_percent": cpu, "uptime": uptime}

    def send_heartbeat(self, interval):
        """Separate thread for heartbeating"""
        while self.monitoring_active and self.ws and self.ws.connected:
            try:
                self.ws.send(json.dumps({"op": 1, "d": self.sequence}))
                time.sleep(interval / 1000.0)  # Convert ms to seconds
            except Exception:
                break

    def update_voice_state(self, guild_id: str, channel_id: str | None, mute=False, deaf=False):
        """Send voice state update via WebSocket"""
        if not self.ws or not self.ws.connected:
            return False
            
        payload = {
            "op": 4,
            "d": {
                "guild_id": guild_id,
                "channel_id": channel_id,
                "self_mute": mute,
                "self_deaf": deaf
            }
        }
        try:
            self.ws.send(json.dumps(payload))
            return True
        except Exception:
            return False

    def join_voice_channel(self, channel_id: str) -> bool:
        if not channel_id:
            return False
            
        try:
            # Get channel info to find guild_id
            ch = requests.get(f"{API}/channels/{channel_id}", headers=self.headers)
            if ch.status_code != 200:
                return False
                
            channel_data = ch.json()
            guild_id = channel_data.get("guild_id")
            if not guild_id:
                return False

            # Use WebSocket to join voice channel
            success = self.update_voice_state(guild_id, channel_id)
            if success:
                self.voice_connected = True
                return True
            return False
            
        except Exception:
            return False

    def leave_voice_channel(self) -> bool:
        if not self.voice_connected:
            return True
            
        try:
            # Find the guild_id we're currently connected to
            # This would typically be stored when joining, but for simplicity:
            if self.config.get("voice_channel_id"):
                ch = requests.get(f"{API}/channels/{self.config['voice_channel_id']}", headers=self.headers)
                if ch.status_code == 200:
                    guild_id = ch.json().get("guild_id")
                    if guild_id:
                        # Send None as channel_id to leave voice channel
                        self.update_voice_state(guild_id, None)
            
            self.voice_connected = False
            return True
        except Exception:
            self.voice_connected = False
            return False

    def _gateway_loop(self, status: str):
        backoff = 1
        while self.monitoring_active:
            try:
                self.ws = websocket.WebSocket()
                self.ws.connect(GATEWAY_URL)
                
                # Receive HELLO
                hello_msg = json.loads(self.ws.recv())
                if hello_msg["op"] != 10:  # Not a HELLO
                    continue
                    
                heartbeat_interval = hello_msg["d"]["heartbeat_interval"]
                
                # Start heartbeat in separate thread
                self.heartbeat_thread = threading.Thread(
                    target=self.send_heartbeat, 
                    args=(heartbeat_interval,),
                    daemon=True
                )
                self.heartbeat_thread.start()

                # Send IDENTIFY
                identify = {
                    "op": 2,
                    "d": {
                        "token": self.token,
                        "properties": {
                            "$os": "Windows 10", 
                            "$browser": "Chrome", 
                            "$device": "Windows"
                        },
                        "presence": {
                            "status": status,
                            "afk": False,
                            "since": 0,
                            "activities": []
                        }
                    }
                }
                self.ws.send(json.dumps(identify))

                # Main message loop
                while self.monitoring_active:
                    try:
                        msg = self.ws.recv()
                        if not msg:
                            continue
                            
                        data = json.loads(msg)
                        op = data.get("op")
                        self.sequence = data.get("s")
                        
                        if op == 0:  # Dispatch event
                            t = data.get("t")
                            if t == "READY":
                                self.session_connected = True
                                self.session_id = data["d"].get("session_id")
                                # Set initial presence
                                self.update_presence()
                            elif t == "VOICE_STATE_UPDATE":
                                # Handle voice state updates
                                voice_data = data["d"]
                                if voice_data.get("user_id") == self.userid:
                                    self.voice_connected = voice_data.get("channel_id") is not None
                                    
                        elif op == 1:  # Heartbeat request
                            self.ws.send(json.dumps({"op": 1, "d": self.sequence}))
                        elif op == 7:  # Reconnect
                            break
                        elif op == 9:  # Invalid session
                            time.sleep(2)
                            break
                        elif op == 11:  # Heartbeat ACK
                            pass  # Heartbeat acknowledged
                            
                    except websocket.WebSocketTimeoutException:
                        continue
                    except websocket.WebSocketConnectionClosedException:
                        break
                    except Exception:
                        break
                        
            except Exception as e:
                print(f"Gateway error: {e}")
            finally:
                self.session_connected = False
                try:
                    if self.ws:
                        self.ws.close()
                except Exception:
                    pass
                    
            if not self.monitoring_active:
                break
                
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)

    def update_presence(self):
        """Update bot presence with current config"""
        if not self.ws or not self.ws.connected:
            return
            
        activities = []
        if self.config.get("custom_status"):
            activities.append({
                "type": 4,  # Custom status
                "state": self.config["custom_status"],
                "name": "Custom Status"
            })
            
        presence = {
            "op": 3,
            "d": {
                "since": 0,
                "activities": activities,
                "status": self.config.get("status", "online"),
                "afk": False
            }
        }
        
        try:
            self.ws.send(json.dumps(presence))
        except Exception:
            pass

    def start_presence(self):
        if self._presence_thread and self._presence_thread.is_alive():
            return
        self._presence_thread = threading.Thread(
            target=self._gateway_loop, 
            args=(self.config.get("status", "online"),), 
            daemon=True
        )
        self._presence_thread.start()

    def stop(self):
        self.monitoring_active = False
        self.leave_voice_channel()
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            pass

    def toggle_voice(self, channel_id: str | None = None) -> str:
        if not self.config.get("auto_join_voice"):
            cid = (channel_id or "").strip()

            if not cid:
                return "missing_channel"
            
            ok = self.join_voice_channel(cid)
            if ok:
                self.config["auto_join_voice"] = True
                self.config["voice_channel_id"] = cid
                save_config(self.config_path, self.config)
                return "connected"
            return "failed"
        
        else:
            self.config["auto_join_voice"] = False
            old_channel_id = self.config.get("voice_channel_id", "")
            self.config["voice_channel_id"] = ""
            save_config(self.config_path, self.config)
            self.leave_voice_channel()
            return "disabled"