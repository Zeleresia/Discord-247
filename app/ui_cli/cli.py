import os
import time
import sys
import select
from pathlib import Path
from dotenv import load_dotenv
from ..core import DiscordBot
from ..config import load_config, save_config

load_dotenv()

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[38;2;115;138;219m'
    LIGHT_CYAN = '\033[38;2;76;228;190m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def move_cursor_home():
    """Move cursor to top-left without clearing screen"""
    print('\033[H', end='')

def move_cursor_to(row, col):
    """Move cursor to specific row and column (1-indexed)"""
    print(f'\033[{row};{col}H', end='')

def clear_from_cursor():
    """Clear from cursor to end of screen"""
    print('\033[J', end='')

def get_terminal_width():
    """Get terminal width, with fallback to 80"""
    try:
        return os.get_terminal_size().columns
    except Exception:
        return 80

def print_center(text: str):
    try:
        cols = get_terminal_width()
        print(text.center(cols))
    except Exception:
        print(text)

def print_header():
    clear_screen()
    width = get_terminal_width()
    print(Colors.CYAN + "=" * width + Colors.END)
    title = f"{'DISCORD BOT CONTROLLER':^{width}}"
    print(Colors.BOLD + Colors.MAGENTA + title + Colors.END)
    print(Colors.CYAN + "=" * width + Colors.END)
    print()

class BotCLI:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.config_path = project_root / "config.json"
        self.config = load_config(self.config_path)
        self.token = os.getenv("DISCORD_TOKEN") or ""
        self.bot: DiscordBot | None = None

    def save_token(self, token: str):
        env_path = self.project_root / ".env"
        with env_path.open("w", encoding="utf-8") as f:
            f.write(f"DISCORD_TOKEN={token}\n")

    def initialize_credentials(self) -> str:
        while True:
            print_header()
            width = get_terminal_width()
            title = f"{'INITIALIZING CREDENTIALS':^{width}}"
            print(Colors.BOLD + title + Colors.END)
            print()
            current = self.token
            if current:
                print(Colors.YELLOW + f"Current token: {current[:20]}..." + Colors.END)
                print(Colors.WHITE + "[1] Use current token" + Colors.END)
                print(Colors.WHITE + "[2] Enter new token" + Colors.END)
                print()
                choice = input(Colors.CYAN + "Select option (1-2): " + Colors.END).strip()
                if choice == "1":
                    if DiscordBot.validate_token(current):
                        return current
                elif choice == "2":
                    newt = input(Colors.CYAN + "\n(IMPORTANT: Your Discord TOKEN must not be share to anyone, or they can login into your account!)\nEnter your Discord token: " + Colors.END).strip()
                    if DiscordBot.validate_token(newt):
                        self.save_token(newt)
                        self.token = newt
                        return newt
                else:
                    print(Colors.RED + "Invalid choice!" + Colors.END); time.sleep(1.5)
            else:
                print(Colors.RED + "No token found in configuration!" + Colors.END)
                print()
                newt = input(Colors.CYAN + "Enter your Discord token: " + Colors.END).strip()
                if DiscordBot.validate_token(newt):
                    self.save_token(newt); self.token = newt; return newt

    def run(self):
        token = self.initialize_credentials()
        clear_screen(); print_header()
        width = get_terminal_width()
        success_msg = f"{'LOGIN SUCCESSFUL!':^{width}}"
        starting_msg = f"{'Starting bot controller...':^{width}}"
        print(Colors.GREEN + success_msg + Colors.END)
        print(Colors.YELLOW + starting_msg + Colors.END)
        time.sleep(2)
        self.bot = DiscordBot(token, self.config_path)
        self.bot.connect()
        self.bot.start_presence()
        self.display_panel()

    def display_panel(self):
        assert self.bot is not None
        
        # Windows-specific imports for non-blocking input
        if os.name == 'nt':
            import msvcrt
        
        # Initial clear and draw static content
        clear_screen()
        print_header()
        
        # Calculate positions
        width = get_terminal_width()
        available_width = width - 8
        col_width = available_width // 5
        
        # Row positions (adjust based on your header size)
        session_row = 5
        table_data_row = 10
        voice_status_row = 14
        console_row = 21
        
        # Draw static UI elements once
        print()
        print()
        
        # Draw table structure
        print(Colors.CYAN + "┌" + "─" * (width - 2) + "┐" + Colors.END)
        header = f" {'Username':^{col_width}} {'RAM':^{col_width}} {'CPU':^{col_width}} {'Uptime':^{col_width}} {'Voice Channel':^{col_width}}"
        print(Colors.CYAN + "│" + Colors.BOLD + header[:width-2].ljust(width - 2) + Colors.END + Colors.CYAN + "│" + Colors.END)
        print(Colors.CYAN + "├" + "─" * (width - 2) + "┤" + Colors.END)
        print(Colors.CYAN + "│" + " " * (width - 2) + "│" + Colors.END)
        print(Colors.CYAN + "└" + "─" * (width - 2) + "┘" + Colors.END)
        print()
        print(Colors.BOLD + "Use keyboard to select:" + Colors.END)
        print(Colors.WHITE + "[1] Voice Channel: " + Colors.END)
        print(Colors.WHITE + "[2] Edit Voice Channel ID" + Colors.END)
        print(Colors.WHITE + "[3] Edit Status" + Colors.END)
        print(Colors.WHITE + "[4] Custom Status" + Colors.END)
        print(Colors.WHITE + "[5] Logout" + Colors.END)
        print()
        print(Colors.YELLOW + "[Console]:" + Colors.END)
        print()
        print()
        print(Colors.CYAN + "Press 1-5 to select (refreshing every 1s)..." + Colors.END)
        
        while self.bot.monitoring_active:
            # Update only dynamic values
            stats = self.bot.get_system_stats()
            uname = self.bot.username or "unknown"
            
            # Update session status
            session_status = "CONNECTED" if self.bot.session_connected else "DISCONNECTED"
            status_color = Colors.LIGHT_CYAN if self.bot.session_connected else Colors.RED
            move_cursor_to(session_row, 1)
            session_text = f"{'[Session: ' + session_status + ']':^{width}}"
            print(status_color + session_text + Colors.END)
            move_cursor_home()
            
            # Update table data row
            move_cursor_to(table_data_row, 2)
            voice_channel = self.bot.config.get("voice_channel_id", "None")
            data = f" {uname:^{col_width}} {str(stats['memory_mb']) + ' MB':^{col_width}} {str(stats['cpu_percent']) + '%':^{col_width}} {stats['uptime']:^{col_width}} {voice_channel:^{col_width}}"
            print(data[:width-2].ljust(width - 2), end='')
            
            # Update voice status
            voice_status = "ON" if self.bot.config.get("auto_join_voice") else "OFF"
            voice_color = Colors.GREEN if self.bot.config.get("auto_join_voice") else Colors.RED
            move_cursor_to(voice_status_row, 23)
            print(voice_color + voice_status + Colors.END + "    ", end='')
            
            # Update console status
            move_cursor_to(console_row, 1)
            if self.bot.config.get("auto_join_voice") and not self.bot.config.get("voice_channel_id"):
                print(Colors.RED + "Warning: auto_join_voice is enabled but no voice_channel_id in config.json" + Colors.END + " " * 20)
            elif self.bot.voice_connected:
                print(Colors.GREEN + "Voice channel: Connected" + Colors.END + " " * 50)
            else:
                print(Colors.YELLOW + "Voice channel: Disconnected" + Colors.END + " " * 50)
            
            sys.stdout.flush()
            
            # Non-blocking key check
            try:
                choice = None
                if os.name == 'nt':
                    if msvcrt.kbhit():
                        choice = msvcrt.getch().decode('utf-8').strip()
                else:
                    import termios
                    import tty
                    old_settings = termios.tcgetattr(sys.stdin)
                    try:
                        tty.setcbreak(sys.stdin.fileno())
                        rlist, _, _ = select.select([sys.stdin], [], [], 1.0)
                        if rlist:
                            choice = sys.stdin.read(1)
                    finally:
                        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                
                if choice:
                    clear_screen()
                    if choice == "1":
                        self.toggle_voice_ui()
                    elif choice == "2":
                        self.edit_voice_channel_id_ui()
                    elif choice == "3":
                        self.edit_status_ui()
                    elif choice == "4":
                        self.edit_activity_ui()
                    elif choice == "5":
                        self.logout_ui()
                        break
                    # Redraw everything after dialog
                    clear_screen()
                    print_header()
                    print()
                    print()
                    print(Colors.CYAN + "┌" + "─" * (width - 2) + "┐" + Colors.END)
                    header = f" {'Username':^{col_width}} {'RAM':^{col_width}} {'CPU':^{col_width}} {'Uptime':^{col_width}} {'Voice Channel':^{col_width}}"
                    print(Colors.CYAN + "│" + Colors.BOLD + header[:width-2].ljust(width - 2) + Colors.END + Colors.CYAN + "│" + Colors.END)
                    print(Colors.CYAN + "├" + "─" * (width - 2) + "┤" + Colors.END)
                    print(Colors.CYAN + "│" + " " * (width - 2) + "│" + Colors.END)
                    print(Colors.CYAN + "└" + "─" * (width - 2) + "┘" + Colors.END)
                    print()
                    print(Colors.BOLD + "Use keyboard to select:" + Colors.END)
                    print(Colors.WHITE + "[1] Voice Channel: " + Colors.END)
                    print(Colors.WHITE + "[2] Edit Voice Channel ID" + Colors.END)
                    print(Colors.WHITE + "[3] Edit Status" + Colors.END)
                    print(Colors.WHITE + "[4] Custom Status" + Colors.END)
                    print(Colors.WHITE + "[5] Logout" + Colors.END)
                    print()
                    print(Colors.YELLOW + "[Console]:" + Colors.END)
                    print()
                    print()
                    print(Colors.CYAN + "Press 1-5 to select (refreshing every 1s)..." + Colors.END)
                else:
                    if os.name == 'nt':
                        time.sleep(1)
            except KeyboardInterrupt:
                self.logout_ui()
                break

    def toggle_voice_ui(self):
        assert self.bot is not None
        
        # If turning ON
        if not self.bot.config.get("auto_join_voice"):
            # Check if voice_channel_id exists
            cid = self.bot.config.get("voice_channel_id", "").strip()
            if not cid:
                print(Colors.RED + "No voice channel ID configured!" + Colors.END)
                print(Colors.YELLOW + "Please use option [2] to set a voice channel ID first." + Colors.END)
                time.sleep(3)
                return
            
            # Try to connect
            res = self.bot.toggle_voice(cid)
            if res == "connected":
                print(Colors.GREEN + "Voice channel enabled and connected!" + Colors.END)
            elif res == "failed":
                print(Colors.RED + "Failed to connect to voice channel!" + Colors.END)
            time.sleep(2)
        
        # If turning OFF
        else:
            # Check if actually connected
            if not self.bot.voice_connected:
                print(Colors.YELLOW + "Voice is enabled but not connected." + Colors.END)
                print(Colors.CYAN + "Do you want to:" + Colors.END)
                print(Colors.WHITE + "[1] Try to reconnect" + Colors.END)
                print(Colors.WHITE + "[2] Turn OFF voice channel" + Colors.END)
                subchoice = input(Colors.CYAN + "Select option (1-2): " + Colors.END).strip()
                
                if subchoice == "1":
                    # Force reconnect
                    cid = self.bot.config.get("voice_channel_id", "").strip()
                    if cid:
                        print(Colors.YELLOW + "Attempting to reconnect..." + Colors.END)
                        success = self.bot.join_voice_channel(cid)
                        if success:
                            print(Colors.GREEN + "Reconnected successfully!" + Colors.END)
                        else:
                            print(Colors.RED + "Failed to reconnect!" + Colors.END)
                    else:
                        print(Colors.RED + "No voice channel ID configured!" + Colors.END)
                    time.sleep(2)
                elif subchoice == "2":
                    # Turn OFF
                    res = self.bot.toggle_voice()
                    if res == "disabled":
                        print(Colors.YELLOW + "Voice channel disabled!" + Colors.END)
                    time.sleep(2)
            else:
                # Already connected, just turn OFF
                res = self.bot.toggle_voice()
                if res == "disabled":
                    print(Colors.YELLOW + "Voice channel disabled!" + Colors.END)
                time.sleep(2)

    def edit_voice_channel_id_ui(self):
        assert self.bot is not None
        
        current_id = self.bot.config.get("voice_channel_id", "")
        if current_id:
            print(Colors.CYAN + f"\nCurrent Voice Channel ID: " + Colors.YELLOW + current_id + Colors.END)
        else:
            print(Colors.YELLOW + "\nNo Voice Channel ID configured." + Colors.END)
        
        print(Colors.WHITE + "Enter new voice channel ID (or press Enter to keep current):" + Colors.END)
        new_id = input(Colors.CYAN + "> " + Colors.END).strip()
        
        if new_id:
            # Update the config
            self.bot.config["voice_channel_id"] = new_id
            save_config(self.config_path, self.bot.config)
            print(Colors.GREEN + "Voice channel ID updated!" + Colors.END)
            
            # If voice is currently enabled, ask to reconnect
            if self.bot.config.get("auto_join_voice"):
                print(Colors.YELLOW + "\nVoice is currently enabled. Reconnecting..." + Colors.END)
                self.bot.leave_voice_channel()
                time.sleep(1)
                success = self.bot.join_voice_channel(new_id)
                if success:
                    print(Colors.GREEN + "Reconnected to new voice channel!" + Colors.END)
                else:
                    print(Colors.RED + "Failed to connect to new voice channel!" + Colors.END)
        else:
            print(Colors.YELLOW + "Voice channel ID unchanged." + Colors.END)
        
        time.sleep(2)

    def edit_status_ui(self):
        assert self.bot is not None
        print(Colors.CYAN + "\nCurrent status: " + Colors.YELLOW + self.bot.config.get("status", "online") + Colors.END)
        print(Colors.WHITE + "Available: online, idle, dnd, invisible" + Colors.END)
        s = input(Colors.CYAN + "Enter new status: " + Colors.END).strip().lower()
        if s in ("online", "idle", "dnd", "invisible"):
            self.bot.config["status"] = s
            save_config(self.config_path, self.bot.config)
            self.bot.update_presence()
            print(Colors.GREEN + "Status updated!" + Colors.END)
        else:
            print(Colors.RED + "Invalid status!" + Colors.END)
        time.sleep(2)

    def edit_activity_ui(self):
        assert self.bot is not None
        cur = self.bot.config.get("custom_status", "")
        print(Colors.CYAN + f"\nCurrent activity: " + Colors.YELLOW + (cur if cur else "None") + Colors.END)
        act = input(Colors.CYAN + "Enter new activity (or empty to clear): " + Colors.END).strip()
        self.bot.config["custom_status"] = act if act else ""
        save_config(self.config_path, self.bot.config)
        self.bot.update_presence()
        print(Colors.GREEN + "Activity updated!" + Colors.END)
        time.sleep(2)

    def logout_ui(self):
        assert self.bot is not None
        self.bot.stop()
        self.bot.leave_voice_channel()
        print(Colors.YELLOW + "\nLogging out...\nPlease run the command again" + Colors.END)
        time.sleep(2)