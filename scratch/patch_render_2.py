with open("scratch/render_final_showcase.py", "r") as f:
    code = f.read()

code = code.replace(
    "    DEMO_PATH = demo_h264\n    DEBUG_PATH = debug_h264",
    "    FINAL_DEMO_PATH = demo_h264\n    FINAL_DEBUG_PATH = debug_h264"
)
code = code.replace("os.path.exists(DEMO_PATH)", "os.path.exists(FINAL_DEMO_PATH)")
code = code.replace("os.path.getsize(DEMO_PATH)", "os.path.getsize(FINAL_DEMO_PATH)")
code = code.replace("demo_cap = cv2.VideoCapture(DEMO_PATH)", "demo_cap = cv2.VideoCapture(FINAL_DEMO_PATH)")
code = code.replace("os.path.abspath(DEMO_PATH)", "os.path.abspath(FINAL_DEMO_PATH)")
code = code.replace("os.path.abspath(DEBUG_PATH)", "os.path.abspath(FINAL_DEBUG_PATH)")

with open("scratch/render_final_showcase.py", "w") as f:
    f.write(code)
print("Patched script again")
