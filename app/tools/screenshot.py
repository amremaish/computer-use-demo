import subprocess
import base64

def take_screenshot():
    """Take screenshot from the VNC (Xvfb) session and return base64-encoded PNG"""
    cmd = "xwd -display :1 -root | convert xwd:- png:-"
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)
    return base64.b64encode(result.stdout).decode("utf-8")

