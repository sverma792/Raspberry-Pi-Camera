# Raspberry Pi Camera — Live Stream Over WiFi

Stream video from a Raspberry Pi camera module to any device on your local
network — just open a web browser, no app installs required.

This uses `picamera2` (Raspberry Pi's official camera library) and Flask to
serve an MJPEG stream over HTTP.

## Hardware

- Raspberry Pi (tested with Pi 4 Model B; works on Pi 3/5 too)
- Any CSI camera module (official Pi Camera, or generic OV5647 / IMX219
  modules like the Inland 5MP 1080p camera)
- Raspberry Pi OS **Bookworm** or later (comes with `picamera2` preinstalled)

## 1. Connect the camera

1. Power off the Pi.
2. Connect the camera's ribbon cable to the CSI port (contacts facing the
   correct direction — usually toward the HDMI port on a Pi 4; check your
   camera's documentation).
3. Power the Pi back on.

Verify the Pi sees the camera:

```bash
rpicam-hello --list-cameras
```

You should see your camera listed. If not, check the ribbon cable seating
and that the camera is enabled in `raspi-config` (`Interface Options` ->
`Camera`, if using an older OS release).

## 2. Install dependencies

```bash
sudo apt update
sudo apt install -y python3-picamera2 python3-flask
```

(`python3-picamera2` and `python3-flask` come from apt because `picamera2`
needs to be tied to the system's libcamera install — installing it via pip
in a virtual environment will not work correctly.)

If you'd rather use pip for Flask only:

```bash
pip install -r requirements.txt --break-system-packages
```

## 3. Run the stream

```bash
python3 app.py
```

You should see:

```
Camera started at 1280x720 @ 24fps
 * Running on http://0.0.0.0:8000
```

## 4. View the stream

Find your Pi's IP address:

```bash
hostname -I
```

Then, from **any device on the same WiFi network** (laptop, phone, tablet —
any browser), go to:

```
http://<raspberry-pi-ip>:8000
```

For example: `http://192.168.1.42:8000`

You can also usually use the Pi's hostname instead of its IP:

```
http://raspberrypi.local:8000
```

## Configuration

Edit the constants at the top of `app.py`:

| Setting        | Default     | Notes                                          |
|----------------|-------------|-------------------------------------------------|
| `PORT`         | `8000`      | Change if 8000 is already in use               |
| `RESOLUTION`   | `1280x720`  | Lower this (e.g. `640x480`) if the stream lags |
| `FRAMERATE`    | `24`        | Lower for weaker WiFi / more clients           |
| `JPEG_QUALITY` | `80`        | Lower = less bandwidth, more compression artifacts |

## Troubleshooting

- **Stream is laggy or choppy**: lower `RESOLUTION` and/or `FRAMERATE`, or
  switch the Pi to a 5GHz WiFi network / wired Ethernet.
- **`picamera2 is not installed` error**: make sure you're on Raspberry Pi
  OS Bookworm or later, and installed it via `apt`, not `pip`.
- **Camera not detected**: re-seat the ribbon cable, make sure it's the
  right way around, and confirm with `rpicam-hello --list-cameras`.
- **Can't reach the stream from another device**: make sure both devices
  are on the same WiFi network, and check the Pi's firewall isn't blocking
  port 8000 (`sudo ufw allow 8000` if `ufw` is enabled).
- **Multiple viewers**: the Flask dev server used here (`threaded=True`)
  can handle a handful of simultaneous viewers fine for casual use. For
  many concurrent viewers or production use, consider expanding to a
  dedicated multi-client streaming server or a WSGI server with more
  worker threads.

## Running it automatically on boot (optional)

Create a systemd service so the stream starts automatically:

```bash
sudo tee /etc/systemd/system/picam-stream.service > /dev/null <<EOF
[Unit]
Description=Raspberry Pi Camera Stream
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/Raspberry-Pi-Camera/app.py
WorkingDirectory=/home/pi/Raspberry-Pi-Camera
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable --now picam-stream.service
```

(Adjust the paths above if you clone the repo somewhere other than
`/home/pi/Raspberry-Pi-Camera`.)

## License

MIT — do whatever you'd like with it.
