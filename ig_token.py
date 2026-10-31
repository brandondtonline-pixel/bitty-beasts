"""Save the Instagram posting token. Runs on Dominic's PC, never in the repo.

    python ig_token.py   # paste the token from the Meta dashboard into the pop-up box

The token is a system-user token from the Bitty Beasts Poster app and never expires, so this
is only needed again if the token is revoked or regenerated. It is saved outside the repo at
~/.bitty-beasts/ig_token and copied into this repo's IG_TOKEN secret with the GitHub CLI.
"""
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog

TOKEN_FILE = Path.home() / '.bitty-beasts' / 'ig_token'
GH = r'C:\Program Files\GitHub CLI\gh.exe'


def main():
    # A pop-up box, because hidden console prompts don't take pastes in every Windows terminal.
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    token = (simpledialog.askstring('Bitty Beasts', 'Paste the Instagram token (Ctrl+V), then click OK:',
                                    show='•', parent=root) or '').strip()
    if not token:
        sys.exit('No token entered, nothing saved.')
    TOKEN_FILE.parent.mkdir(exist_ok=True)
    TOKEN_FILE.write_text(token)
    subprocess.run([GH, 'secret', 'set', 'IG_TOKEN'], input=token, text=True, check=True,
                   cwd=Path(__file__).parent)
    messagebox.showinfo('Bitty Beasts', 'Saved! The token is stored on this PC and in GitHub.', parent=root)
    root.destroy()


if __name__ == '__main__':
    main()
