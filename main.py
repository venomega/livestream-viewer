#!/usr/bin/python3
import subprocess
import sys
import time
import sdl2
import sdl2.ext
import numpy as np
import cv2
import threading

class VideoStream:
    def __init__(self, url):
        self.url = url
        self.cap = cv2.VideoCapture(url)
        self.frame = None
        self.running = True

        if not self.cap.isOpened():
            print(f"Error: No se puede abrir el stream {url}")
            self.running = False

        self.thread = threading.Thread(target=self.update)
        self.thread.start()

    def update(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                self.frame = frame

    def get_frame(self):
        return self.frame

    def stop(self):
        self.running = False
        self.cap.release()
        self.thread.join()

def main():
    # Configuración de los streams RTSP
    RTSP_URLS = [
        "rtsp://asd:123456ASD@192.168.2.153:554/cam/realmonitor?channel=1&subtype=0",
        "rtsp://asd:123456ASD@192.168.2.153:554/cam/realmonitor?channel=2&subtype=0",
        "rtsp://asd:123456ASD@192.168.2.153:554/cam/realmonitor?channel=3&subtype=0",
        "rtsp://asd:123456ASD@192.168.2.153:554/cam/realmonitor?channel=4&subtype=0",
        "rtsp://asd:123456ASD@192.168.2.153:554/cam/realmonitor?channel=5&subtype=0",
        "rtsp://asd:123456ASD@192.168.2.153:554/cam/realmonitor?channel=6&subtype=0"
        "rtsp://asd:123456ASD@192.168.2.153:554/cam/realmonitor?channel=7&subtype=0"
        "rtsp://asd:123456ASD@192.168.2.153:554/cam/realmonitor?channel=8&subtype=0"
    ]

    # Inicializar SDL2
    sdl2.ext.init()
    window = sdl2.ext.Window("RTSP Stream", size=(1680, 1050), flags=sdl2.SDL_WINDOW_RESIZABLE)
    window.show()
    renderer = sdl2.ext.Renderer(window)

    # Crear una lista de flujos de video
    streams = [VideoStream(url) for url in RTSP_URLS]

    # Variable para saber si hay un stream maximizado
    maximized_index = None

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
                    # Obtener posición del mouse
                    mouse_x = event.button.x
                    mouse_y = event.button.y
                    display_w, display_h = window.size
                    panel_w = display_w // 3
                    panel_h = display_h // 2
                    col = mouse_x // panel_w
                    row = mouse_y // panel_h
                    idx = int(row * 3 + col)
                    if 0 <= idx < len(streams):
                        maximized_index = idx
                else:
                    # Si ya hay uno maximizado, cualquier clic restaura la vista
                    maximized_index = None

        display_w, display_h = window.size
        panel_w = display_w // 3
        panel_h = display_h // 2

        renderer.clear()
        if maximized_index is None:
            # Renderizar todos los streams
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
                    x = (i % 3) * panel_w
                    y = (i // 3) * panel_h
                    sdl2.SDL_RenderCopy(renderer.sdlrenderer, texture, None, sdl2.SDL_Rect(x, y, panel_w, panel_h))
                    sdl2.SDL_DestroyTexture(texture)
        else:
            # Renderizar solo el stream maximizado
            stream = streams[maximized_index]
            frame = stream.get_frame()
            if frame is not None:
                # Redimensionar a toda la ventana
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
