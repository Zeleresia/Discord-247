import os
from pathlib import Path
from dotenv import load_dotenv
from app.ui_cli.cli import BotCLI

def main():
    load_dotenv()
    project_root = Path(__file__).resolve().parent
    cli = BotCLI(project_root)
    cli.run()

if __name__ == "__main__":
    main()
