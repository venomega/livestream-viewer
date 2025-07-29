# Live Stream Viewer

A powerful, multi-stream video viewer built with Python, SDL2, and FFmpeg. Supports RTSP, HLS, HTTP streams, and more with real-time audio/video synchronization.

## 🚀 Features

### Core Functionality
- **Multi-stream Support**: View multiple video streams simultaneously in a dynamic grid layout
- **Dynamic Layout**: Automatically adjusts grid size based on number of streams (N columns = √N, rows = N/columns)
- **Fullscreen Mode**: Native fullscreen support with automatic screen resolution detection
- **Click to Maximize**: Click any stream to view it fullscreen, click again to return to grid view
- **Audio Support**: Stream-specific audio playback when maximizing streams
- **Real-time **: Handles live streams content

### Technical Features
- **FFmpeg Integration**: Uses FFmpeg for robust stream handling and decoding
- **SDL2 Rendering**: Hardware-accelerated video rendering with SDL2
- **Threaded Architecture**: Separate threads for video, audio, and error handling
- **Error Recovery**: Automatic reconnection and error handling for unstable streams
- **Memory Management**: Efficient buffer management to prevent memory leaks
- **Cross-platform**: Works on Linux (tested on Arch Linux)

### Audio Features
- **Stream-specific Audio**: Each stream can have its own audio track
- **Audio Switching**: Automatically switches audio when maximizing different streams
- **Master Audio Control**: Global audio control with 'M' key
- **Audio Detection**: Automatically detects and handles streams with/without audio

### User Interface
- **Keyboard Controls**:
  - `ESC`: Exit application
  - `M`: Toggle master audio stream
- **Mouse Controls**:
  - Click stream panel: Maximize stream
  - Click maximized stream: Return to grid view
- **Dynamic Resizing**: Window automatically adjusts to screen resolution

## 📋 Requirements

### System Requirements
- Linux (tested on Arch Linux)
- Python 3.8+
- FFmpeg
- FFprobe

### Python Dependencies
```bash
pip install sdl2 numpy opencv-python sounddevice
```

### System Dependencies
```bash
# Arch Linux / Manjaro
sudo pacman -S ffmpeg python-sdl2 python-numpy python-opencv python-sounddevice

# Ubuntu / Debian
sudo apt install ffmpeg python3-sdl2 python3-numpy python3-opencv python3-sounddevice

# Fedora
sudo dnf install ffmpeg python3-sdl2 python3-numpy python3-opencv python3-sounddevice
```

## 🛠️ Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd live-stream-viewer
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Create streams configuration**:
Create a `streams.txt` file with your stream URLs:
```txt
# Live camera streams
rtsp://user:pass@192.168.1.100:554/stream1
rtsp://user:pass@192.168.1.101:554/stream2

# HLS streams
https://example.com/stream1.m3u8
https://example.com/stream2.m3u8

```

## 🎮 Usage

### Basic Usage
```bash
# Run with normal output (no debug logs)
python3 main.py

# Run with debug output
python3 main.py -debug
```

### Stream Configuration
The application reads stream URLs from `streams.txt`. Each line should contain one stream URL:
- Lines starting with `#` are comments
- Empty lines are ignored
- Supported formats: RTSP, HLS, HTTP, HTTPS

### Controls
- **Mouse**: Click any stream panel to maximize it
- **Mouse**: Click maximized stream to return to grid view
- **Keyboard**: Press `M` to toggle master audio
- **Keyboard**: Press `ESC` to exit

## 🔧 Configuration

### Stream File Format
```txt
# Comments start with #
# Empty lines are ignored

# RTSP streams
rtsp://username:password@ip:port/stream

# HLS streams
https://example.com/playlist.m3u8

```

### Debug Mode
Enable debug output to see detailed information about:
- Stream accessibility checks
- FFmpeg process creation
- Frame reading statistics
- Audio buffer status
- Error messages

```bash
python3 main.py -debug
```

## 🏗️ Architecture

### Core Components
1. **VideoStream Class**: Manages individual stream processing
2. **FFmpeg Integration**: Handles video/audio decoding
3. **SDL2 Rendering**: Hardware-accelerated video display
4. **Threading System**: Separate threads for video, audio, and error handling

### Thread Architecture
- **Main Thread**: UI event handling and rendering
- **Video Thread**: Frame reading from FFmpeg
- **Audio Thread**: Audio processing and playback
- **Error Thread**: FFmpeg error monitoring

### Stream Processing Pipeline
1. **Stream Validation**: Check accessibility and capabilities
2. **FFmpeg Process**: Launch FFmpeg with appropriate parameters
3. **Frame Reading**: Read raw video frames from FFmpeg stdout
4. **Audio Processing**: Read audio data from FFmpeg stderr (if available)
5. **Rendering**: Convert frames to SDL2 textures and display

## 🐛 Troubleshooting

### Common Issues

**Streams not loading**:
- Check network connectivity
- Verify stream URLs are accessible
- Run with `-debug` flag to see detailed error messages

**Audio not working**:
- Ensure stream has audio track
- Check system audio configuration
- Verify sounddevice installation

**Performance issues**:
- Reduce number of simultaneous streams
- Check CPU/GPU usage
- Monitor network bandwidth

**FFmpeg errors**:
- Update FFmpeg to latest version
- Check stream format compatibility
- Verify stream accessibility

### Debug Information
When running with `-debug`, you'll see:
- Stream accessibility checks
- FFmpeg process creation details
- Frame reading statistics
- Audio buffer information
- Error messages and warnings

## 🤝 Contributing

We welcome contributions! Please feel free to submit issues, feature requests, or pull requests.

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

### Code Style
- Follow PEP 8 guidelines
- Add comments for complex logic
- Include debug output for troubleshooting
- Test with multiple stream types

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Support

If you find this project useful, please consider supporting its development.

### Crypto Donations

**Monero (XMR)**:
```
8A7Yz8K9vL2mN3qR5sT6uV7wX8yZ9aB0cD1eF2gH3iJ4kL5mN6oP7qR8sT9uV0wX1yZ2aB3cD4eF5gH6iJ7kL8mN9oP0qR1sT2uV3wX4yZ5aB6cD7eF8gH9iJ0kL1mN2oP3qR4sT5uV6wX7yZ8aB9cD0eF1gH2iJ3kL4mN5oP6qR7sT8uV9wX0yZ1aB2cD3eF4gH5iJ6kL7mN8oP9qR0sT1uV2wX3yZ4aB5cD6eF7gH8iJ9kL0mN1oP2qR3sT4uV5wX6yZ7aB8cD9eF0gH1iJ2kL3mN4oP5qR6sT7uV8wX9yZ0aB1cD2eF3gH4iJ5kL6mN7oP8qR9sT0uV1wX2yZ3aB4cD5eF6gH7iJ8kL9mN0oP1qR2sT3uV4wX5yZ6aB7cD8eF9gH0iJ1kL2mN3oP4qR5sT6uV7wX8yZ9aB0cD1eF2gH3iJ4kL5mN6oP7qR8sT9uV0wX1yZ2aB3cD4eF5gH6iJ7kL8mN9oP0qR1sT2uV3wX4yZ5aB6cD7eF8gH9iJ0kL1mN2oP3qR4sT5uV6wX7yZ8aB9cD0eF1gH2iJ3kL4mN5oP6qR7sT8uV9wX0yZ1aB2cD3eF4gH5iJ6kL7mN8oP9qR0sT1uV2wX3yZ4aB5cD6eF7gH8iJ9kL0mN1oP2qR3sT4uV5wX6yZ7aB8cD9eF0gH1iJ2kL3mN4oP5qR6sT7uV8wX9yZ0aB1cD2eF3gH4iJ5kL6mN7oP8qR9sT0uV1wX2yZ3aB4cD5eF6gH7iJ8kL9mN0oP1qR2sT3uV4wX5yZ6aB7cD8eF9gH0iJ1kL2mN3oP4qR5sT6uV7wX8yZ9aB0cD1eF2gH3iJ4kL5mN6oP7qR8sT9uV0wX1yZ2aB3cD4eF5gH6iJ7kL8mN9oP0qR1sT2uV3wX4yZ5aB6cD7eF8gH9iJ0kL1mN2oP3qR4sT5uV6wX7yZ8aB9cD0eF1gH2iJ3kL4mN5oP6qR7sT8uV9wX0yZ1aB2cD3eF4gH5iJ6kL7mN8oP9qR0sT1uV2wX3yZ4aB5cD6eF7gH8iJ9kL0mN1oP2qR3sT4uV5wX6yZ7aB8cD9eF0gH1
