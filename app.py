#!/usr/bin/env python3
"""
Raspberry Pi Camera — MJPEG live stream over your local network.

Run this on the Raspberry Pi. Any device on the same Wi-Fi network can then
open a web browser and go to:

    http://<raspberry-pi-ip>:8000

...to see the live camera feed. No app installs needed on the viewing side.

Requires:
    - picamera2 (preinstalled on Raspberry Pi OS Bookworm and later)
    - Flask (pip install flask --break-system-packages)
"""

import io
import time
import threading
import logging

from flask import Flask, Response, render_template_string

try:
    from picamera2 import Picamera2
    from picamera2.encoders import JpegEncoder
    from picamera2.outputs import FileOutput
    PICAMERA_AVAILABLE = True
except ImportError:
    PICAMERA_AVAILABLE = False

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
HOST = "0.0.0.0"        # listen on all network interfaces
PORT = 8000              # browse to http://<pi-ip>:8000
RESOLUTION = (1280, 720)  # (width, height) - lower this if the stream lags
FRAMERATE = 24            # target frames per second
JPEG_QUALITY = 80         # 1-100, higher = better quality but more bandwidth

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("picam-stream")


class StreamingOutput(io.BufferedIOBase):
    """
    A thread-safe buffer that holds the most recent JPEG frame.
    Picamera2's MJPEGEncoder writes frames into this as they're captured;
    the Flask route below reads the latest frame out whenever a client
    is ready for the next one.
    """

    def __init__(self):
        self.frame = None
        self.condition = threading.Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()


class Camera:
    """Wraps Picamera2 and starts continuous MJPEG capture into a StreamingOutput."""

    def __init__(self, resolution=RESOLUTION, framerate=FRAMERATE):
        if not PICAMERA_AVAILABLE:
            raise RuntimeError(
                "picamera2 is not installed. This script must run on a "
                "Raspberry Pi with Raspberry Pi OS Bookworm (or later), "
                "which ships picamera2 by default."
            )
        self.output = StreamingOutput()
        self.picam2 = Picamera2()
        video_config = self.picam2.create_video_configuration(
            main={"size": resolution}
        )
        self.picam2.configure(video_config)
        self.picam2.set_controls({"FrameRate": framerate})
        # JpegEncoder is the software JPEG encoder and accepts a "q" (quality)
        # parameter. (Note: picamera2's MJPEGEncoder is a *hardware* V4L2
        # encoder that only takes a bitrate, not a quality value — that's
        # the wrong class for this use case.)
        self.encoder = JpegEncoder(q=JPEG_QUALITY)

    def start(self):
        self.picam2.start_recording(self.encoder, FileOutput(self.output))
        log.info("Camera started at %sx%s @ %sfps", *RESOLUTION, FRAMERATE)

    def stop(self):
        self.picam2.stop_recording()

    def get_frame(self):
        with self.output.condition:
            self.output.condition.wait()
            return self.output.frame


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
app = Flask(__name__)
camera = None  # initialized in main()

PAGE = """
<!doctype html>
<html>
  <head>
    <title>Raspberry Pi Camera Stream</title>
    <style>
      body { background:#111; color:#eee; font-family: sans-serif; text-align:center; margin:0; padding:2rem; }
      h1 { font-weight: 500; }
      img { max-width: 95vw; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
    </style>
  </head>
  <body>
    <h1>Raspberry Pi Camera — Live</h1>
    <img src="{{ url_for('video_feed') }}">
  </body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(PAGE)


def mjpeg_generator():
    while True:
        frame = camera.get_frame()
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
        )


@app.route("/video_feed")
def video_feed():
    return Response(
        mjpeg_generator(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


def main():
    global camera
    camera = Camera()
    camera.start()
    try:
        app.run(host=HOST, port=PORT, threaded=True)
    finally:
        camera.stop()


if __name__ == "__main__":
    main()
