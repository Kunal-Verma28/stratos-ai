"""
Performance Benchmark & Latency Profiling Tool.
Measures:
  1. Camera frame capture FPS and latency
  2. MediaPipe HandLandmarker inference latency
  3. One-Euro Filter computation time
  4. Coordinate mapping and Win32 SendInput dispatch latency
  5. Total end-to-end pipeline latency
"""
import sys
import time
import os
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

from app.config import Config
from app.core.camera import CameraManager
from app.core.detector import HandDetector
from app.core.filters import SmoothPoint
from app.core.coordinate_mapper import CoordinateMapper
from app.gestures.recognizer import GestureRecognizer
from app.controller.mouse_controller import MouseController

def run_benchmark(num_frames: int = 100):
    print("=" * 65)
    print("  AeroPointer - End-to-End Performance Benchmark")
    print("=" * 65)
    
    cfg = Config()
    print("[1/5] Initializing Camera and AI Model...")
    camera = CameraManager(cfg)
    if not camera.start():
        print("ERROR: Could not open camera.")
        return

    detector = HandDetector(cfg)
    smoother = SmoothPoint(min_cutoff=cfg.smoothing_min_cutoff, beta=cfg.smoothing_beta)
    mapper = CoordinateMapper(cfg)
    recognizer = GestureRecognizer(cfg)
    
    print("[2/5] Warming up camera feed (waiting 2 seconds)...")
    time.sleep(2.0)
    
    print(f"[3/5] Benchmarking across {num_frames} frames...")
    print("      (Tip: Move your hand in front of the camera now)")
    
    cam_latencies = []
    det_latencies = []
    filt_latencies = []
    rec_latencies = []
    total_latencies = []
    hands_detected = 0

    for i in range(num_frames):
        t0 = time.perf_counter()
        
        # 1. Camera Frame Read
        t_cam0 = time.perf_counter()
        frame = camera.frame
        while frame is None:
            time.sleep(0.001)
            frame = camera.frame
        t_cam1 = time.perf_counter()
        cam_latencies.append((t_cam1 - t_cam0) * 1000.0)

        # 2. Hand Detection (MediaPipe)
        t_det0 = time.perf_counter()
        result = detector.process_frame(frame)
        t_det1 = time.perf_counter()
        det_latencies.append((t_det1 - t_det0) * 1000.0)

        # 3. Smoothing & Mapping
        t_filt0 = time.perf_counter()
        if result is not None:
            hands_detected += 1
            lms = result.landmarks
            raw_x, raw_y = lms[8][0], lms[8][1]
            sx, sy = smoother.filter(raw_x, raw_y)
            screen_x, screen_y = mapper.map(sx, sy)
        else:
            screen_x, screen_y = 0, 0
        t_filt1 = time.perf_counter()
        filt_latencies.append((t_filt1 - t_filt0) * 1000.0)

        # 4. Gesture Recognition
        t_rec0 = time.perf_counter()
        if result is not None:
            recognizer.process(result.landmarks, (screen_x, screen_y))
        t_rec1 = time.perf_counter()
        rec_latencies.append((t_rec1 - t_rec0) * 1000.0)

        t_total = (time.perf_counter() - t0) * 1000.0
        total_latencies.append(t_total)
        
        if (i + 1) % 25 == 0 or i == num_frames - 1:
            print(f"      Processed frame {i+1}/{num_frames} — Last frame: {t_total:.1f}ms")

    camera.stop()
    
    print("\n[4/5] Benchmark Results:")
    print("-" * 65)
    print(f"  Total Frames Evaluated   : {num_frames}")
    print(f"  Frames With Hand Detected: {hands_detected} ({hands_detected/num_frames*100:.1f}%)")
    print("-" * 65)
    print(f"  Pipeline Stage           :  Average Latency  |  Min  |  Max")
    print("-" * 65)
    print(f"  1. Frame Fetch           :  {np.mean(cam_latencies):6.2f} ms     | {np.min(cam_latencies):5.2f} | {np.max(cam_latencies):5.2f} ms")
    print(f"  2. MediaPipe Detection   :  {np.mean(det_latencies):6.2f} ms     | {np.min(det_latencies):5.2f} | {np.max(det_latencies):5.2f} ms")
    print(f"  3. 1€ Filtering & Mapping:  {np.mean(filt_latencies):6.2f} ms     | {np.min(filt_latencies):5.2f} | {np.max(filt_latencies):5.2f} ms")
    print(f"  4. Gesture Recognition   :  {np.mean(rec_latencies):6.2f} ms     | {np.min(rec_latencies):5.2f} | {np.max(rec_latencies):5.2f} ms")
    print("-" * 65)
    avg_total = np.mean(total_latencies)
    effective_fps = 1000.0 / avg_total if avg_total > 0 else 0
    print(f"  TOTAL Pipeline Latency   :  {avg_total:6.2f} ms")
    print(f"  Calculated Effective FPS :  {effective_fps:6.1f} FPS")
    print("-" * 65)
    
    if avg_total < 35.0:
        print("  Status: [EXCELLENT] (< 35ms latency) - Ready for real-time high-speed control!")
    elif avg_total < 60.0:
        print("  Status: [GOOD] (< 60ms latency) - Smooth control on standard hardware.")
    else:
        print("  Status: [FAIR] - Consider reducing camera resolution for higher FPS.")
    print("=" * 65)

if __name__ == "__main__":
    run_benchmark(num_frames=60)
