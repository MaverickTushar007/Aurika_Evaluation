import re

with open("scratch/render_final_showcase.py", "r") as f:
    code = f.read()

# Replace DEMO_PATH to be the raw one, and demo_h264 to be the final one
code = code.replace(
    'DEMO_PATH = os.path.join(FINAL_DIR, "restaurant_analytics_v3_final.mp4")',
    'DEMO_PATH = os.path.join(FINAL_DIR, "restaurant_analytics_v3_final_raw.mp4")'
)
code = code.replace(
    'DEBUG_PATH = os.path.join(FINAL_DIR, "tracking_debug.mp4")',
    'DEBUG_PATH = os.path.join(FINAL_DIR, "tracking_debug_raw.mp4")'
)

# Update ffmpeg commands
old_ffmpeg = """    print("[transcode] Transcoding output videos to H.264 format...")
    demo_h264 = os.path.join(FINAL_DIR, "restaurant_analytics_v3_final_h264.mp4")
    debug_h264 = os.path.join(FINAL_DIR, "tracking_debug_h264.mp4")
    
    subprocess.run(["/opt/homebrew/bin/ffmpeg", "-y", "-i", DEMO_PATH, "-c:v", "libx264", "-pix_fmt", "yuv420p", demo_h264], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["/opt/homebrew/bin/ffmpeg", "-y", "-i", DEBUG_PATH, "-c:v", "libx264", "-pix_fmt", "yuv420p", debug_h264], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    os.rename(demo_h264, DEMO_PATH)
    os.rename(debug_h264, DEBUG_PATH)"""

new_ffmpeg = """    print("[transcode] Transcoding output videos to H.264 format...")
    demo_h264 = os.path.join(FINAL_DIR, "restaurant_analytics_v3_final.mp4")
    debug_h264 = os.path.join(FINAL_DIR, "tracking_debug.mp4")
    
    print("Running FFmpeg for Demo video...")
    subprocess.run(["/opt/homebrew/bin/ffmpeg", "-y", "-i", DEMO_PATH, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", demo_h264], check=True)
    
    print("Running FFmpeg for Debug video...")
    subprocess.run(["/opt/homebrew/bin/ffmpeg", "-y", "-i", DEBUG_PATH, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", debug_h264], check=True)
    
    # We will verify the final H264 files instead of the raw ones
    DEMO_PATH = demo_h264
    DEBUG_PATH = debug_h264"""

code = code.replace(old_ffmpeg, new_ffmpeg)

with open("scratch/render_final_showcase.py", "w") as f:
    f.write(code)
print("Patched render_final_showcase.py")
