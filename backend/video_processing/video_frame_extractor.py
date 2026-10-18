import cv2
import json
import os
import argparse


def extract_frames(video_path, output_dir, interval_seconds=1.0):
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be greater than 0")

    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)

    try:
        if not cap.isOpened():
            raise ValueError(f"Unable to open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)

        if fps is None or fps <= 0:
            raise ValueError(f"Invalid FPS for video: {video_path}")

        frame_interval = max(1, int(round(fps * interval_seconds)))

        extracted_frames = []
        frame_number = 0
        saved_frame_number = 0

        while True:
            success, frame = cap.read()

            if not success:
                break

            if frame_number % frame_interval == 0:
                timestamp_seconds = frame_number / fps

                filename = (
                    f"frame_{saved_frame_number:04d}_"
                    f"{timestamp_seconds:.2f}s.jpg"
                )

                filepath = os.path.join(output_dir, filename)

                write_success = cv2.imwrite(filepath, frame)

                if not write_success:
                    raise IOError(f"Failed to write frame: {filepath}")

                extracted_frames.append({
                    "frame_id": saved_frame_number,
                    "timestamp_seconds": round(timestamp_seconds, 2),
                    "filename": filename
                })

                saved_frame_number += 1

            frame_number += 1

        manifest_path = os.path.join(output_dir, "frames_manifest.json")

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(extracted_frames, f, indent=2)

        return {
            "video_path": video_path,
            "output_dir": output_dir,
            "frames_extracted": len(extracted_frames),
            "manifest": manifest_path
        }

    finally:
        cap.release()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract timestamped frames from a video."
    )

    parser.add_argument(
        "--video",
        required=True,
        help="Path to input video"
    )

    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where extracted frames will be stored"
    )

    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=1.0,
        help="Frame extraction interval in seconds"
    )

    args = parser.parse_args()

    result = extract_frames(
        video_path=args.video,
        output_dir=args.output_dir,
        interval_seconds=args.interval_seconds
    )

    print(json.dumps(result, indent=2))
