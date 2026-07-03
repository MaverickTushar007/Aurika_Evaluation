# scratch/check_videos.py
import cv2

for video in ["test_seated6.mp4", "test_seated3.mkv", "Dark_lighting.mp4"]:
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    print(f"Video: {video} | FPS: {fps:.1f} | Frame Count: {frame_count:.0f} | Resolution: {w:.0f}x{h:.0f}")
    cap.release()
