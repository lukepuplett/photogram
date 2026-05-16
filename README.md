# Photogram

A command-line tool for automated 3D reconstruction from image sequences using photogrammetry.

## What is Photogrammetry?

Photogrammetry converts 2D images (taken from multiple angles) into precise 3D models. The tool automates the entire pipeline:

1. **Feature Detection & Matching** — Identifies distinctive points across images
2. **Structure from Motion (SfM)** — Solves for camera positions and 3D point locations
3. **Bundle Adjustment** — Refines all parameters for maximum accuracy
4. **Multi-View Stereo (MVS)** — Creates dense depth maps and point clouds
5. **Export** — Saves the result as 3D geometry (OBJ, PLY, etc.)

## Workflow Checklist

- [ ] Collect 20-50 overlapping JPEG images of your subject
- [ ] Run `photogram process ./images --output model.obj`
- [ ] Load the OBJ file in any 3D viewer (Meshlab, Blender, etc.)
- [ ] Profit!

## Project Structure

```
photogram/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── setup.py                  # Package configuration
├── src/
│   └── photogram/
│       ├── __init__.py
│       ├── cli.py            # Command-line interface
│       ├── processor.py       # Main photogrammetry pipeline
│       └── utils.py          # Utility functions
├── tests/
│   ├── __init__.py
│   └── test_processor.py     # Unit tests
├── data/
│   └── sample_images/        # Your JPEG images go here
└── output/
    └── (generated 3D models)
```

## Installation

### Prerequisites

1. **Python 3.8+** (you have 3.11.8 ✓)
2. **COLMAP** — The core photogrammetry engine (free, open-source)

### Step 1: Install COLMAP

On macOS with Homebrew:
```bash
brew install colmap
```

On Linux:
```bash
sudo apt-get install colmap
```

On Windows: Download from https://github.com/colmap/colmap/releases

### Step 2: Clone & Install Python Package

```bash
cd photogram
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Usage

```bash
# Basic usage
photogram process ./path/to/images --output model.obj

# With options (future)
photogram process ./images --output model.obj --quality high --format ply
```

## What Each Stage Does

| Stage | Tool | Input | Output |
|-------|------|-------|--------|
| Feature matching | OpenCV + COLMAP | JPEG images | Camera poses, sparse points |
| Reconstruction | COLMAP SfM | Matched features | Calibrated camera intrinsics |
| Dense matching | COLMAP MVS | Calibrated cameras | Dense point cloud |
| Export | Open3D | Point cloud | OBJ / PLY file |

## Development

Run tests:
```bash
pytest tests/
```

## License

MIT

## References

- [COLMAP Documentation](https://colmap.github.io/)
- [Open3D Documentation](http://www.open3d.org/)
- [Photogrammetry Fundamentals](https://en.wikipedia.org/wiki/Photogrammetry)
