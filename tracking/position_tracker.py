import numpy as np
import uuid
import cv2

class PositionTracker:
    def __init__(self, max_distance=150, max_missing_frames=150):
        self.tracks = {}
        self.max_distance = max_distance
        self.max_missing_frames = max_missing_frames

    def _centroid(self, bbox):
        x1, y1, x2, y2 = bbox
        return ((x1+x2)/2, (y1+y2)/2)

    def update(self, detections, frame_id, ts, frame_gray=None, confs=None, signatures=None):
        results = []
        matched_tokens = set()

        for bbox in detections:
            centroid = self._centroid(bbox)
            best_token, best_dist = None, float('inf')

            for token, track in self.tracks.items():
                if token in matched_tokens:
                    continue
                dist = np.sqrt(
                    (centroid[0]-track['centroid'][0])**2 +
                    (centroid[1]-track['centroid'][1])**2
                )
                if dist < best_dist:
                    best_dist = dist
                    best_token = token

            if best_token and best_dist < self.max_distance:
                self.tracks[best_token].update({
                    'centroid': centroid, 'bbox': bbox,
                    'last_frame': frame_id, 'last_ts': ts
                })
                matched_tokens.add(best_token)
                results.append((best_token, bbox, False))
            else:
                token = str(uuid.uuid4())[:8]
                self.tracks[token] = {
                    'centroid': centroid, 'bbox': bbox,
                    'last_frame': frame_id, 'entry_ts': ts,
                    'last_ts': ts
                }
                matched_tokens.add(token)
                results.append((token, bbox, True))

        return results

    def get_exited(self, frame_id):
        exited = []
        for token, track in list(self.tracks.items()):
            if (frame_id - track['last_frame']) > self.max_missing_frames:
                exited.append((token, track['entry_ts'], track['last_ts']))
                del self.tracks[token]
        return exited

    def flush_all(self):
        return [(t, tr['entry_ts'], tr['last_ts']) for t, tr in self.tracks.items()]

def calculate_iou(box1, box2):
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2
    xi1 = max(x1_1, x1_2)
    yi1 = max(y1_1, y1_2)
    xi2 = min(x2_1, x2_2)
    yi2 = min(y2_1, y2_2)
    inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)
    box1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
    box2_area = (x2_2 - x1_2) * (y2_2 - y1_2)
    union_area = box1_area + box2_area - inter_area
    return inter_area / max(union_area, 1.0)

class ByteTracker:
    def __init__(self, max_distance=150, max_missing_frames=150):
        self.tracks = {}
        self.max_missing_frames = max_missing_frames

    def update(self, detections, frame_id, ts, frame_gray=None, confs=None, signatures=None):
        results = []
        high_dets, low_dets = [], []
        if confs is None:
            confs = [1.0] * len(detections)
        if signatures is None:
            signatures = [None] * len(detections)
            
        for box, conf, sig in zip(detections, confs, signatures):
            if conf >= 0.5:
                high_dets.append((box, conf, sig))
            else:
                low_dets.append((box, conf, sig))
        
        matched_tracks = set()
        for box, conf, sig in high_dets:
            best_token, best_iou = None, 0.2
            for token, tr in self.tracks.items():
                if token in matched_tracks:
                    continue
                iou = calculate_iou(box, tr['bbox'])
                if iou > best_iou:
                    best_iou = iou
                    best_token = token
            if best_token:
                self.tracks[best_token].update({'bbox': box, 'last_frame': frame_id, 'last_ts': ts})
                matched_tracks.add(best_token)
                results.append((best_token, box, False))
            else:
                token = str(uuid.uuid4())[:8]
                self.tracks[token] = {'bbox': box, 'last_frame': frame_id, 'entry_ts': ts, 'last_ts': ts}
                matched_tracks.add(token)
                results.append((token, box, True))
                
        for box, conf, sig in low_dets:
            best_token, best_iou = None, 0.2
            for token, tr in self.tracks.items():
                if token in matched_tracks:
                    continue
                iou = calculate_iou(box, tr['bbox'])
                if iou > best_iou:
                    best_iou = iou
                    best_token = token
            if best_token:
                self.tracks[best_token].update({'bbox': box, 'last_frame': frame_id, 'last_ts': ts})
                matched_tracks.add(best_token)
                results.append((best_token, box, False))
        return results

    def get_exited(self, frame_id):
        exited = []
        for token, track in list(self.tracks.items()):
            if (frame_id - track['last_frame']) > self.max_missing_frames:
                exited.append((token, track['entry_ts'], track['last_ts']))
                del self.tracks[token]
        return exited

    def flush_all(self):
        return [(t, tr['entry_ts'], tr['last_ts']) for t, tr in self.tracks.items()]

class OCSORTTracker:
    def __init__(self, max_distance=150, max_missing_frames=150):
        self.tracks = {}
        self.max_missing_frames = max_missing_frames

    def update(self, detections, frame_id, ts, frame_gray=None, confs=None, signatures=None):
        results = []
        matched = set()
        for box in detections:
            cx = (box[0] + box[2]) / 2.0
            cy = (box[1] + box[3]) / 2.0
            best_token, best_score = None, -1.0
            for token, tr in self.tracks.items():
                if token in matched:
                    continue
                pred_cx = tr['cx'] + tr.get('vx', 0.0)
                pred_cy = tr['cy'] + tr.get('vy', 0.0)
                dist = np.sqrt((cx - pred_cx)**2 + (cy - pred_cy)**2)
                iou = calculate_iou(box, tr['bbox'])
                score = iou - (dist / 1000.0)
                if score > best_score:
                    best_score = score
                    best_token = token
            if best_token and best_score > -0.2:
                tr = self.tracks[best_token]
                vx = cx - tr['cx']
                vy = cy - tr['cy']
                self.tracks[best_token].update({
                    'cx': cx, 'cy': cy, 'vx': vx, 'vy': vy, 'bbox': box, 'last_frame': frame_id, 'last_ts': ts
                })
                matched.add(best_token)
                results.append((best_token, box, False))
            else:
                token = str(uuid.uuid4())[:8]
                self.tracks[token] = {
                    'cx': cx, 'cy': cy, 'vx': 0.0, 'vy': 0.0, 'bbox': box, 'last_frame': frame_id, 'entry_ts': ts, 'last_ts': ts
                }
                matched.add(token)
                results.append((token, box, True))
        return results

    def get_exited(self, frame_id):
        exited = []
        for token, track in list(self.tracks.items()):
            if (frame_id - track['last_frame']) > self.max_missing_frames:
                exited.append((token, track['entry_ts'], track['last_ts']))
                del self.tracks[token]
        return exited

    def flush_all(self):
        return [(t, tr['entry_ts'], tr['last_ts']) for t, tr in self.tracks.items()]

class DeepSORTTracker:
    def __init__(self, max_distance=150, max_missing_frames=150):
        self.tracks = {}
        self.max_missing_frames = max_missing_frames

    def update(self, detections, frame_id, ts, frame_gray=None, confs=None, signatures=None):
        results = []
        matched = set()
        if signatures is None:
            signatures = [np.zeros((125,), dtype=np.float32)] * len(detections)
            
        for box, sig in zip(detections, signatures):
            cx = (box[0] + box[2]) / 2.0
            cy = (box[1] + box[3]) / 2.0
            best_token, best_score = None, -1.0
            for token, tr in self.tracks.items():
                if token in matched:
                    continue
                app_score = cv2.compareHist(sig, tr['sig'], cv2.HISTCMP_CORREL) if sig.any() and tr['sig'].any() else 0.0
                dist = np.sqrt((cx - tr['cx'])**2 + (cy - tr['cy'])**2)
                if dist < 150.0:
                    score = app_score * 0.7 + (calculate_iou(box, tr['bbox']) * 0.3)
                    if score > best_score:
                        best_score = score
                        best_token = token
            if best_token and best_score > 0.3:
                self.tracks[best_token].update({
                    'cx': cx, 'cy': cy, 'bbox': box, 'sig': sig, 'last_frame': frame_id, 'last_ts': ts
                })
                matched.add(best_token)
                results.append((best_token, box, False))
            else:
                token = str(uuid.uuid4())[:8]
                self.tracks[token] = {
                    'cx': cx, 'cy': cy, 'bbox': box, 'sig': sig, 'last_frame': frame_id, 'entry_ts': ts, 'last_ts': ts
                }
                matched.add(token)
                results.append((token, box, True))
        return results

    def get_exited(self, frame_id):
        exited = []
        for token, track in list(self.tracks.items()):
            if (frame_id - track['last_frame']) > self.max_missing_frames:
                exited.append((token, track['entry_ts'], track['last_ts']))
                del self.tracks[token]
        return exited

    def flush_all(self):
        return [(t, tr['entry_ts'], tr['last_ts']) for t, tr in self.tracks.items()]

class BoTSORTTracker:
    def __init__(self, max_distance=150, max_missing_frames=150):
        self.tracks = {}
        self.max_missing_frames = max_missing_frames
        self.last_frame_gray = None

    def update_camera_motion(self, frame_gray):
        if self.last_frame_gray is None:
            self.last_frame_gray = frame_gray
            return 0.0, 0.0
        h, w = frame_gray.shape
        ch, cw = h // 2, w // 2
        patch = self.last_frame_gray[ch-30:ch+30, cw-30:cw+30]
        res = cv2.matchTemplate(frame_gray[ch-40:ch+40, cw-40:cw+40], patch, cv2.TM_CCOEFF)
        _, _, _, max_loc = cv2.minMaxLoc(res)
        dx = max_loc[0] - 10
        dy = max_loc[1] - 10
        self.last_frame_gray = frame_gray
        return dx, dy

    def update(self, detections, frame_id, ts, frame_gray=None, confs=None, signatures=None):
        dx, dy = 0.0, 0.0
        if frame_gray is not None:
            dx, dy = self.update_camera_motion(frame_gray)
            
        results = []
        matched = set()
        for box in detections:
            cx = (box[0] + box[2]) / 2.0
            cy = (box[1] + box[3]) / 2.0
            best_token, best_iou = None, 0.2
            for token, tr in self.tracks.items():
                if token in matched:
                    continue
                shifted_box = [tr['bbox'][0] + dx, tr['bbox'][1] + dy, tr['bbox'][2] + dx, tr['bbox'][3] + dy]
                iou = calculate_iou(box, shifted_box)
                if iou > best_iou:
                    best_iou = iou
                    best_token = token
            if best_token:
                self.tracks[best_token].update({
                    'cx': cx, 'cy': cy, 'bbox': box, 'last_frame': frame_id, 'last_ts': ts
                })
                matched.add(best_token)
                results.append((best_token, box, False))
            else:
                token = str(uuid.uuid4())[:8]
                self.tracks[token] = {
                    'cx': cx, 'cy': cy, 'bbox': box, 'last_frame': frame_id, 'entry_ts': ts, 'last_ts': ts
                }
                matched.add(token)
                results.append((token, box, True))
        return results

    def get_exited(self, frame_id):
        exited = []
        for token, track in list(self.tracks.items()):
            if (frame_id - track['last_frame']) > self.max_missing_frames:
                exited.append((token, track['entry_ts'], track['last_ts']))
                del self.tracks[token]
        return exited

    def flush_all(self):
        return [(t, tr['entry_ts'], tr['last_ts']) for t, tr in self.tracks.items()]

class StrongSORTTracker:
    def __init__(self, max_distance=150, max_missing_frames=150):
        self.tracks = {}
        self.max_missing_frames = max_missing_frames

    def update(self, detections, frame_id, ts, frame_gray=None, confs=None, signatures=None):
        results = []
        matched = set()
        if signatures is None:
            signatures = [np.zeros((125,), dtype=np.float32)] * len(detections)
            
        for box, sig in zip(detections, signatures):
            cx = (box[0] + box[2]) / 2.0
            cy = (box[1] + box[3]) / 2.0
            best_token, best_score = None, -1.0
            for token, tr in self.tracks.items():
                if token in matched:
                    continue
                app_score = cv2.compareHist(sig, tr['sig'], cv2.HISTCMP_CORREL) if sig.any() and tr['sig'].any() else 0.0
                dist = np.sqrt((cx - tr['cx'])**2 + (cy - tr['cy'])**2)
                iou = calculate_iou(box, tr['bbox'])
                score = (app_score * 0.5) + (iou * 0.4) - (dist / 1000.0 * 0.1)
                if score > best_score:
                    best_score = score
                    best_token = token
            if best_token and best_score > 0.2:
                self.tracks[best_token].update({
                    'cx': cx, 'cy': cy, 'bbox': box, 'sig': sig, 'last_frame': frame_id, 'last_ts': ts
                })
                matched.add(best_token)
                results.append((best_token, box, False))
            else:
                token = str(uuid.uuid4())[:8]
                self.tracks[token] = {
                    'cx': cx, 'cy': cy, 'bbox': box, 'sig': sig, 'last_frame': frame_id, 'entry_ts': ts, 'last_ts': ts
                }
                matched.add(token)
                results.append((token, box, True))
        return results

    def get_exited(self, frame_id):
        exited = []
        for token, track in list(self.tracks.items()):
            if (frame_id - track['last_frame']) > self.max_missing_frames:
                exited.append((token, track['entry_ts'], track['last_ts']))
                del self.tracks[token]
        return exited

    def flush_all(self):
        return [(t, tr['entry_ts'], tr['last_ts']) for t, tr in self.tracks.items()]
