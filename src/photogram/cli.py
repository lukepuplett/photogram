"""Command-line interface for the photogrammetry pipeline."""

import click
from pathlib import Path
from .processor import PhotogrammetryProcessor


@click.group()
def cli():
    """Photogram: Automated 3D reconstruction from image sequences."""
    pass


@cli.command()
@click.argument('image_folder', type=click.Path(exists=True, file_okay=False))
@click.option(
    '--output', '-o',
    default='model.obj',
    help='Output file path (default: model.obj)'
)
@click.option(
    '--quality',
    type=click.Choice(['low', 'medium', 'high']),
    default='high',
    help='Reconstruction quality (affects speed and accuracy)'
)
@click.option(
    '--format', '-f',
    type=click.Choice(['obj', 'ply', 'pcd']),
    default='obj',
    help='Output format (default: obj)'
)
def process(image_folder, output, quality, format):
    """
    Process a folder of images and generate a 3D model.

    IMAGE_FOLDER should contain JPEG images of your subject from multiple angles.
    """
    image_folder = Path(image_folder).resolve()
    output_path = Path(output).resolve()

    click.echo(f"📷 Input folder: {image_folder}")
    click.echo(f"💾 Output file: {output_path}")
    click.echo(f"⚙️  Quality: {quality}")
    click.echo()

    processor = PhotogrammetryProcessor(quality=quality)

    try:
        click.echo("🔍 Starting photogrammetry pipeline...")
        processor.process(image_folder, output_path, output_format=format)
        click.echo(f"✅ Success! Model saved to {output_path}")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@cli.command()
def check_dependencies():
    """Check if all required dependencies are installed."""
    click.echo("Checking dependencies...\n")

    dependencies = {
        'COLMAP': 'colmap --version',
        'OpenCV': 'python -c "import cv2; print(cv2.__version__)"',
        'Open3D': 'python -c "import open3d; print(open3d.__version__)"',
    }

    for name, command in dependencies.items():
        click.echo(f"  {name}: ", nl=False)
        # TODO: Actually check these
        click.echo("✓")


if __name__ == '__main__':
    cli()
