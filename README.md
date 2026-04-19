# flippy

Command-line tool for working with Nintendo Flipnote Studio animations (.ppm and .kwz formats).

Built on [flipnote.py](https://github.com/meemo/flipnote.py), which is accelerated by [libugomemo](https://github.com/meemo/libugomemo).

## Installation

```sh
pip install flippy-cli
```

## Usage

```sh
flippy meta animation.ppm
flippy meta animation.kwz

flippy extract audio --track=0 animation.ppm output.wav
flippy extract audio --track=mix animation.kwz output.wav

flippy extract thumbnail animation.kwz thumb.bin
flippy extract frames animation.ppm frames/
```

## Features

- Parse and display metadata as JSON for PPM, KWZ, and other Flipnote formats
- Extract audio tracks to WAV with ADPCM decoding
- Extract thumbnails and animation frames to BMP
- Signature verification using built-in public keys
