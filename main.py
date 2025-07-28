#!/usr/bin/python3
import subprocess
import sys
import time
import sdl2
import sdl2.ext
import numpy as np
import cv2
import threading
import math
import json
import sounddevice as sd
import os
import re
import argparse

# Variable global para debug
DEBUG = False

def debug_print(*args, **kwargs):
    """Función para imprimir solo si debug está habilitado"""
    if DEBUG:
        print(*args, **kwargs)

def setup_debug():
    """Configurar debug basado en argumentos de línea de comandos"""
    global DEBUG
    parser = argparse.ArgumentParser(description='RTSP Stream Viewer')
    parser.add_argument('-debug', action='store_true', help='Enable debug output')
    args = parser.parse_args()
def get_screen_size():
    """Obtener el tamaño de la pantalla usando xrandr"""
    try:
        result = subprocess.run(['xrandr'], capture_output=True, text=True)
        # Buscar la línea que contiene la resolución activa
        for line in result.stdout.split('\n'):
            if '*' in line:  # La línea con * indica la resolución activa
                match = re.search(r'(\d+)x(\d+)', line)
                if match:
                    width = int(match.group(1))
                    height = int(match.group(2))
                    debug_print(f"Screen size detected: {width}x{height}")
                    return width, height
        # Si no encuentra, usar valores por defecto
        debug_print("Could not detect screen size, using default 1920x1080")
        return 1920, 1080
    except Exception as e:
        debug_print(f"Error getting screen size: {e}, using default 1920x1080")
        return 1920, 1080

class VideoStream:
    def __init__(self, url, width, height, has_audio=False):
        self.url = url
        self.width = width
        self.height = height
        self.frame = None
        self.running = True
        self.audio_running = False
        self.audio_thread = None
        self.audio_pipe = None
        self.audio_buffer = []
        self.audio_lock = threading.Lock()
        self.has_audio = has_audio

        # Configurar ffmpeg según si tiene audio o no
        ffmpeg_cmd = [
            'ffmpeg',
            '-loglevel', 'error',
            '-protocol_whitelist', 'file,http,https,tcp,tls,crypto',
            '-reconnect', '1',
            '-reconnect_streamed', '1',
            '-reconnect_delay_max', '5',
            '-fflags', '+genpts',
            '-avoid_negative_ts', 'make_zero',
            '-i', url,
            '-c:v', 'rawvideo',
            '-pix_fmt', 'bgr24',
            '-vsync', '0',
            '-an',  # sin audio en stdout
            '-f', 'rawvideo',
            'pipe:1'
        ]
        
        # Solo agregar audio si el stream tiene audio
        if has_audio:
            ffmpeg_cmd.extend([
                '-f', 's16le',
                '-acodec', 'pcm_s16le',
                '-ac', '2',
                '-ar', '44100',
                'pipe:2'
            ])

        self.proc = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=10**8
        )
        self.audio_pipe = self.proc.stderr
        debug_print(f"FFmpeg process started for {url} (PID: {self.proc.pid})")

        # Hilo para leer errores de ffmpeg
        self.error_thread = threading.Thread(target=self._error_reader)
        self.error_thread.start()

        self.thread = threading.Thread(target=self.update)
        self.thread.start()
        
        # Solo crear hilo de audio si el stream tiene audio
        if has_audio:
            self.audio_reader_thread = threading.Thread(target=self._audio_reader)
            self.audio_reader_thread.start()
        else:
            self.audio_reader_thread = None

    def update(self):
        frame_size = self.width * self.height * 3
        consecutive_errors = 0
        frames_received = 0
        while self.running:
            raw_frame = self.proc.stdout.read(frame_size)
            if len(raw_frame) == frame_size:
                frames_received += 1
                if frames_received % 30 == 0:  # Cada 30 frames
                    debug_print(f"Received {frames_received} frames from {self.url}")
            if len(raw_frame) != frame_size:
                consecutive_errors += 1
                debug_print(f"Frame size mismatch: expected {frame_size}, got {len(raw_frame)} from {self.url}")
                if consecutive_errors > 10:
                    debug_print(f"Too many consecutive errors reading frames from {self.url}")
                    break
                continue
            consecutive_errors = 0
            frame = np.frombuffer(raw_frame, np.uint8).reshape((self.height, self.width, 3))
            self.frame = frame

    def get_frame(self):
        return self.frame

    def is_working(self):
        """Verificar si el stream está funcionando correctamente"""
        if self.proc.poll() is not None:
            debug_print(f"FFmpeg process for {self.url} has terminated")
            return False
        return self.frame is not None

    def _error_reader(self):
        """Hilo para leer errores de ffmpeg"""
        while self.running:
            try:
                error_line = self.proc.stderr.readline()
                if error_line:
                    debug_print(f"FFmpeg error for {self.url}: {error_line.decode().strip()}")
            except:
                break

    def _audio_reader(self):
        """Hilo que lee continuamente el audio del pipe"""
        blocksize = 4096
        channels = 2
        debug_print(f"Audio reader started for {self.url}")
        bytes_read = 0
        while self.running:
            try:
                data = self.audio_pipe.read(blocksize * channels * 2)
                bytes_read += len(data)
                if data:
                    with self.audio_lock:
                        self.audio_buffer.append(data)
                        # Mantener solo los últimos 10 bloques para evitar memoria infinita
                        if len(self.audio_buffer) > 10:
                            self.audio_buffer.pop(0)
                        if len(self.audio_buffer) % 5 == 0:  # Solo imprimir cada 5 bloques
                            debug_print(f"Audio buffer size: {len(self.audio_buffer)}, total bytes: {bytes_read}")
                else:
                    time.sleep(0.01)  # Esperar un poco si no hay datos
            except Exception as e:
                debug_print(f"Error reading audio: {e}")
                break
        debug_print(f"Audio reader stopped for {self.url}, total bytes read: {bytes_read}")

    def start_audio(self):
        if not self.has_audio:
            debug_print(f"Cannot start audio for {self.url} - no audio stream")
            return
        if self.audio_running:
            return
        debug_print(f"Starting audio for {self.url}")
        self.audio_running = True
        self.audio_thread = threading.Thread(target=self._audio_loop)
        self.audio_thread.start()

    def stop_audio(self):
        if not self.audio_running:
            return
        debug_print(f"Stopping audio for {self.url}")
        self.audio_running = False
        if self.audio_thread is not None:
            self.audio_thread.join()
            self.audio_thread = None

    def _audio_loop(self):
        samplerate = 44100
        channels = 2
        blocksize = 4096
        debug_print(f"Audio loop started for {self.url}")
        try:
            stream = sd.RawOutputStream(samplerate=samplerate, channels=channels, dtype='int16', blocksize=blocksize)
            stream.start()
            try:
                while self.audio_running:
                    with self.audio_lock:
                        if self.audio_buffer:
                            data = self.audio_buffer.pop(0)
                            stream.write(data)
                            debug_print(f"Playing audio block, remaining: {len(self.audio_buffer)}")
                        else:
                            time.sleep(0.01)  # Esperar si no hay datos
            finally:
                stream.stop()
                stream.close()
        except Exception as e:
            debug_print(f"Error in audio loop: {e}")
        debug_print(f"Audio loop stopped for {self.url}")

    def stop(self):
        self.running = False
        self.stop_audio()
        self.proc.kill()
        self.thread.join()
        if self.audio_reader_thread:
            self.audio_reader_thread.join()
        self.error_thread.join()
        if self.audio_pipe:
            self.audio_pipe.close()

def get_stream_size(url):
    cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height',
        '-of', 'json',
        url
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    info = json.loads(result.stdout)
    width = info['streams'][0]['width']
    height = info['streams'][0]['height']
    return width, height

def test_stream_accessibility(url):
    """Verificar si un stream es accesible"""
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'stream=codec_type',
        '-of', 'json',
        url
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        if result.returncode == 0:
            info = json.loads(result.stdout)
            has_video = any(stream.get('codec_type') == 'video' for stream in info.get('streams', []))
            has_audio = any(stream.get('codec_type') == 'audio' for stream in info.get('streams', []))
            debug_print(f"Stream {url} is accessible, has video: {has_video}, has audio: {has_audio}")
            return True, has_audio
        else:
            debug_print(f"Stream {url} is not accessible (return code: {result.returncode})")
            return False, False
    except subprocess.TimeoutExpired:
        debug_print(f"Stream {url} timeout")
        return False, False
    except Exception as e:
        debug_print(f"Stream {url} error: {e}")
        return False, False

def main():
    setup_debug()
    
    # Configuración de los streams RTSP
    RTSP_URLS = [
            "https://s81.ipcamlive.com/streams_timeshift/285cbf3053597caa2/stream.m3u8",
            "https://s61.ipcamlive.com/streams/3dblxt98eyv3wus5q/stream.m3u8",
            "https://streaming.novazion.com/HotelCarre/hotelcarre.stream/playlist.m3u8",
    ]

    # Inicializar SDL2
    sdl2.ext.init()
    screen_width, screen_height = get_screen_size()
    window = sdl2.ext.Window("RTSP Stream", size=(screen_width, screen_height), flags=sdl2.SDL_WINDOW_RESIZABLE)
    window.show()
    renderer = sdl2.ext.Renderer(window)

    # Crear una lista de flujos de video
    streams = []
    for url in RTSP_URLS:
        debug_print(f"\n--- Testing stream: {url} ---")
        is_accessible, has_audio = test_stream_accessibility(url)
        if not is_accessible:
            debug_print(f"Skipping {url} - not accessible")
            continue
        
        try:
            width, height = get_stream_size(url)
        except Exception as e:
            debug_print(f"No se pudo obtener tamaño de {url}: {e}, usando 640x480")
            width, height = 640, 480
        streams.append(VideoStream(url, width, height, has_audio))
        debug_print(f"Successfully created stream for {url}")
    
    debug_print(f"\nTotal streams created: {len(streams)}")
    if len(streams) == 0:
        debug_print("No streams could be created. Exiting.")
        return

    # Variable para saber si hay un stream maximizado
    maximized_index = None
    current_audio_stream = None

    # Bucle principal
    running = True
    mute = True
    mute_cmd = "mpv --quiet --no-terminal --vo=null rtsp://asd:123456ASD@192.168.2.153:554/cam/realmonitor?channel=2&subtype=0"
    mute_proc = object()
    while running:
        for event in sdl2.ext.get_events():
            if event.type == sdl2.SDL_QUIT:
                running = False
            elif event.type == sdl2.SDL_KEYDOWN:
                if event.key.keysym.sym == sdl2.SDLK_ESCAPE:
                    running = False
                elif event.key.keysym.sym == sdl2.SDLK_m:
                    # Alternar mute
                    mute = not mute
                    if mute:
                        mute_proc.kill()
                    else:
                        # Ejecutar comando para reproducir el stream con sonido
                        mute_proc = subprocess.Popen(mute_cmd.split())
            elif event.type == sdl2.SDL_MOUSEBUTTONDOWN:
                if maximized_index is None:
                    mouse_x = event.button.x
                    mouse_y = event.button.y
                    display_w, display_h = window.size
                    N = len(streams)
                    columnas = int(math.ceil(N ** 0.5))
                    filas = int(math.ceil(N / columnas))
                    panel_w = display_w // columnas
                    panel_h = display_h // filas
                    col = mouse_x // panel_w
                    row = mouse_y // panel_h
                    idx = int(row * columnas + col)
                    if 0 <= idx < N:
                        # Iniciar audio del stream maximizado
                        if current_audio_stream is not None:
                            current_audio_stream.stop_audio()
                        streams[idx].start_audio()
                        current_audio_stream = streams[idx]
                        maximized_index = idx
                else:
                    # Detener audio del stream maximizado
                    if current_audio_stream is not None:
                        current_audio_stream.stop_audio()
                        current_audio_stream = None
                    maximized_index = None

        display_w, display_h = window.size
        N = len(streams)
        columnas = int(math.ceil(N ** 0.5))
        filas = int(math.ceil(N / columnas))
        panel_w = display_w // columnas
        panel_h = display_h // filas

        renderer.clear()
        if maximized_index is None:
            for i, stream in enumerate(streams):
                if not stream.is_working():
                    continue
                frame = stream.get_frame()
                if frame is not None:
                    frame_resized = cv2.resize(frame, (panel_w, panel_h), interpolation=cv2.INTER_AREA)
                    frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
                    texture = sdl2.SDL_CreateTexture(
                        renderer.sdlrenderer,
                        sdl2.SDL_PIXELFORMAT_RGB24,
                        sdl2.SDL_TEXTUREACCESS_STREAMING,
                        panel_w, panel_h
                    )
                    sdl2.SDL_UpdateTexture(texture, None, frame_rgb.ctypes.data, panel_w * 3)
                    x = (i % columnas) * panel_w
                    y = (i // columnas) * panel_h
                    sdl2.SDL_RenderCopy(renderer.sdlrenderer, texture, None, sdl2.SDL_Rect(x, y, panel_w, panel_h))
                    sdl2.SDL_DestroyTexture(texture)
        else:
            stream = streams[maximized_index]
            if not stream.is_working():
                debug_print(f"Maximized stream {maximized_index} is not working")
                maximized_index = None
                continue
            frame = stream.get_frame()
            if frame is not None:
                frame_resized = cv2.resize(frame, (display_w, display_h), interpolation=cv2.INTER_AREA)
                frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
                texture = sdl2.SDL_CreateTexture(
                    renderer.sdlrenderer,
                    sdl2.SDL_PIXELFORMAT_RGB24,
                    sdl2.SDL_TEXTUREACCESS_STREAMING,
                    display_w, display_h
                )
                sdl2.SDL_UpdateTexture(texture, None, frame_rgb.ctypes.data, display_w * 3)
                sdl2.SDL_RenderCopy(renderer.sdlrenderer, texture, None, sdl2.SDL_Rect(0, 0, display_w, display_h))
                sdl2.SDL_DestroyTexture(texture)

        renderer.present()
        time.sleep(0.01)

    # Liberar recursos
    for stream in streams:
        stream.stop()
    sdl2.ext.quit()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        debug_print(f"Error: {e}")
        sys.exit(1)
