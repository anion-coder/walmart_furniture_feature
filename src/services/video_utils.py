import cv2
import numpy as np
from typing import List
from PIL import Image

class VideoProcessor:
    def extract_key_frames(self, video_path: str, num_frames: int = 5) -> List[np.ndarray]:
        """Extract key frames from video"""
        
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {video_path}")
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if total_frames == 0:
            raise ValueError("Video file contains no frames")
        
        # Calculate frame indices
        frame_indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
        frames = []
        
        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            
            if ret:
                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(frame_rgb)
        
        cap.release()
        
        if not frames:
            raise ValueError("No frames could be extracted from video")
        
        return frames
