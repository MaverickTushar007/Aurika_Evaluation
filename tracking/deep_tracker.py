import numpy as np
import uuid
import torch
import torchvision.transforms as T
from torchvision.models import resnet18
import logging

logger = logging.getLogger(__name__)

# Try importing torchreid for production-grade ReID backbones
try:
    import torchreid
    HAS_TORCHREID = True
except ImportError:
    HAS_TORCHREID = False

class DeepTracker:
    def __init__(self, max_distance=80, max_missing_frames=100, reid_threshold=0.60):
        self.tracks = {}
        self.max_distance = max_distance
        self.max_missing_frames = max_missing_frames
        self.reid_threshold = reid_threshold
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self._load_reid()

    def _load_reid(self):
        """Loads a real person ReID model configuration (OSNet or equivalent)."""
        self.transform = T.Compose([
            T.ToPILImage(),
            T.Resize((256, 128)),  # OSNet preferred input size
            T.ToTensor(),
            T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])

        if HAS_TORCHREID:
            try:
                # Initialize real OSNet x1_0 architecture
                logger.info("Initializing torchreid OSNet x1_0 model for person ReID.")
                self.model = torchreid.models.build_model(
                    name="osnet_x1_0",
                    num_classes=1000,  # default
                    pretrained=True
                )
                self.model.eval().to(self.device)
                self.is_experimental_backbone = False
                return
            except Exception as e:
                logger.warning(f"Could not load torchreid pretrained weights ({e}). Falling back to classification backbone.")

        # Fallback classification backbone - explicitly labeled as Experimental
        logger.warning("[EXPERIMENTAL_BACKBONE] Utilizing pre-trained ImageNet ResNet-18 as a fallback tracker backbone.")
        self.model = resnet18(pretrained=True)
        self.model.fc = torch.nn.Identity()
        self.model.eval().to(self.device)
        self.is_experimental_backbone = True

    def _embedding(self, frame, bbox):
        x1, y1, x2, y2 = [int(v) for v in bbox]
        crop = frame[max(0, y1):max(0, y2), max(0, x1):max(0, x2)]
        if crop.size == 0:
            return None
        t = self.transform(crop).unsqueeze(0).to(self.device)
        with torch.no_grad():
            feat = self.model(t).cpu().numpy()[0]
            # Normalize embedding (L2 Norm) for cosine similarity
            norm = np.linalg.norm(feat)
            if norm > 1e-8:
                feat = feat / norm
            return feat

    def _cosine(self, a, b):
        if a is None or b is None:
            return 1.0
        # Since embeddings are L2 normalized, cosine distance is 1 - dot product
        return 1.0 - np.dot(a, b)

    def _centroid(self, bbox):
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    def _iou(self, b1, b2):
        ix1, iy1 = max(b1[0], b2[0]), max(b1[1], b2[1])
        ix2, iy2 = min(b1[2], b2[2]), min(b1[3], b2[3])
        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        a1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
        a2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
        return inter / (a1 + a2 - inter + 1e-8)

    def update(self, detections, frame_id, ts, frame=None):
        results = []
        matched_tokens = set()

        for bbox in detections:
            centroid = self._centroid(bbox)
            emb = self._embedding(frame, bbox) if frame is not None else None

            best_token, best_score = None, float('inf')
            for token, track in self.tracks.items():
                if token in matched_tokens:
                    continue
                dist = np.sqrt(
                    (centroid[0] - track['centroid'][0]) ** 2 +
                    (centroid[1] - track['centroid'][1]) ** 2
                )
                iou = self._iou(bbox, track['bbox'])
                cos = self._cosine(emb, track.get('embedding'))
                score = 0.4 * min(dist / self.max_distance, 1.0) + 0.3 * (1 - iou) + 0.3 * cos
                if score < best_score:
                    best_score = score
                    best_token = token

            if best_token and best_score < self.reid_threshold:
                self.tracks[best_token].update({
                    'centroid': centroid, 'bbox': bbox,
                    'last_frame': frame_id, 'last_ts': ts,
                    'embedding': emb
                })
                matched_tokens.add(best_token)
                results.append((best_token, bbox, False))
            else:
                token = str(uuid.uuid4())[:8]
                self.tracks[token] = {
                    'centroid': centroid, 'bbox': bbox,
                    'last_frame': frame_id, 'entry_ts': ts,
                    'last_ts': ts, 'embedding': emb
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
