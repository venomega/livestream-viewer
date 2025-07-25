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

class VideoStream:
    def __init__(self, url, width, height):
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

        self.proc = subprocess.Popen(
            [
                'ffmpeg',
                '-loglevel', 'error',
                '-i', url,
                '-f', 'rawvideo',
                '-pix_fmt', 'bgr24',
                '-an',  # sin audio en stdout
                'pipe:1',
                '-f', 's16le',
                '-acodec', 'pcm_s16le',
                '-ac', '2',
                '-ar', '44100',
                'pipe:2'
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=10**8
        )
        self.audio_pipe = self.proc.stderr
        print(f"FFmpeg process started for {url}")

        self.thread = threading.Thread(target=self.update)
        self.thread.start()
        
        # Hilo separado para leer audio continuamente
        self.audio_reader_thread = threading.Thread(target=self._audio_reader)
        self.audio_reader_thread.start()

    def update(self):
        frame_size = self.width * self.height * 3
        while self.running:
            raw_frame = self.proc.stdout.read(frame_size)
            if len(raw_frame) != frame_size:
                continue
            frame = np.frombuffer(raw_frame, np.uint8).reshape((self.height, self.width, 3))
            self.frame = frame

    def get_frame(self):
        return self.frame

    def _audio_reader(self):
        """Hilo que lee continuamente el audio del pipe"""
        blocksize = 4096
        channels = 2
        print(f"Audio reader started for {self.url}")
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
                            print(f"Audio buffer size: {len(self.audio_buffer)}, total bytes: {bytes_read}")
                else:
                    time.sleep(0.01)  # Esperar un poco si no hay datos
            except Exception as e:
                print(f"Error reading audio: {e}")
                break
        print(f"Audio reader stopped for {self.url}, total bytes read: {bytes_read}")

    def start_audio(self):
        if self.audio_running:
            return
        print(f"Starting audio for {self.url}")
        self.audio_running = True
        self.audio_thread = threading.Thread(target=self._audio_loop)
        self.audio_thread.start()

    def stop_audio(self):
        if not self.audio_running:
            return
        print(f"Stopping audio for {self.url}")
        self.audio_running = False
        if self.audio_thread is not None:
            self.audio_thread.join()
            self.audio_thread = None

    def _audio_loop(self):
        samplerate = 44100
        channels = 2
        blocksize = 4096
        print(f"Audio loop started for {self.url}")
        try:
            stream = sd.RawOutputStream(samplerate=samplerate, channels=channels, dtype='int16', blocksize=blocksize)
            stream.start()
            try:
                while self.audio_running:
                    with self.audio_lock:
                        if self.audio_buffer:
                            data = self.audio_buffer.pop(0)
                            stream.write(data)
                            print(f"Playing audio block, remaining: {len(self.audio_buffer)}")
                        else:
                            time.sleep(0.01)  # Esperar si no hay datos
            finally:
                stream.stop()
                stream.close()
        except Exception as e:
            print(f"Error in audio loop: {e}")
        print(f"Audio loop stopped for {self.url}")

    def stop(self):
        self.running = False
        self.stop_audio()
        self.proc.kill()
        self.thread.join()
        self.audio_reader_thread.join()
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

def check_stream_audio(url):
    """Verificar si el stream tiene audio"""
    cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'a:0',
        '-show_entries', 'stream=codec_type',
        '-of', 'json',
        url
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        info = json.loads(result.stdout)
        has_audio = len(info.get('streams', [])) > 0
        print(f"Stream {url} has audio: {has_audio}")
        return has_audio
    except:
        print(f"Stream {url} has audio: False (error checking)")
        return False

def main():
    # Configuración de los streams RTSP
    RTSP_URLS = [
        "rtsp://asd:123456ASD@192.168.2.153:554/cam/realmonitor?channel=1&subtype=0",
        "rtsp://asd:123456ASD@192.168.2.153:554/cam/realmonitor?channel=2&subtype=0",
        "rtsp://asd:123456ASD@192.168.2.153:554/cam/realmonitor?channel=3&subtype=0",
        "rtsp://asd:123456ASD@192.168.2.153:554/cam/realmonitor?channel=4&subtype=0",
        "rtsp://asd:123456ASD@192.168.2.153:554/cam/realmonitor?channel=5&subtype=0",
        "rtsp://asd:123456ASD@192.168.2.153:554/cam/realmonitor?channel=6&subtype=0",
        "https://rt-esp.rttv.com/dvr/rtesp/playlist_800Kb.m3u8"
    ]
    RTSP_URLS = [
        "rtsp://asd:123456ASD@192.168.2.153:554/cam/realmonitor?channel=2&subtype=0",
        "rtsp://asd:123456ASD@192.168.2.153:554/cam/realmonitor?channel=6&subtype=0",]

    # Inicializar SDL2
    sdl2.ext.init()
    window = sdl2.ext.Window("RTSP Stream", size=(1680, 1050), flags=sdl2.SDL_WINDOW_RESIZABLE)
    window.show()
    renderer = sdl2.ext.Renderer(window)

    # Crear una lista de flujos de video
    streams = []
    for url in RTSP_URLS:
        check_stream_audio(url)
        try:
            width, height = get_stream_size(url)
        except Exception as e:
            print(f"No se pudo obtener tamaño de {url}: {e}, usando 640x480")
            width, height = 640, 480
        streams.append(VideoStream(url, width, height))

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
        print(f"Error: {e}")
        sys.exit(1)
