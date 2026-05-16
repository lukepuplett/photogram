"""Core photogrammetry processing pipeline."""

import subprocess
import tempfile
from pathlib import Path
from typing import Optional
import open3d as o3d
from .utils import find_images, validate_images


class PhotogrammetryProcessor:
    """Orchestrates the photogrammetry pipeline using COLMAP."""

    def __init__(self, quality: str = 'high'):
        """
        Initialize the processor.

        Args:
            quality: One of 'low', 'medium', 'high'
        """
        self.quality = quality
        self._set_colmap_params()

    def _set_colmap_params(self):
        """Set COLMAP parameters based on quality setting."""
        if self.quality == 'low':
            self.max_image_size = 1024
            self.descriptor_type = 'sift'
        elif self.quality == 'medium':
            self.max_image_size = 2048
            self.descriptor_type = 'sift'
        else:  # high
            self.max_image_size = 4096
            self.descriptor_type = 'sift'

    def process(self, image_folder: Path, output_path: Path, output_format: str = 'obj'):
        """
        Run the complete photogrammetry pipeline.

        Args:
            image_folder: Path to folder containing JPEG images
            output_path: Path for output 3D model
            output_format: Output format ('obj', 'ply', or 'pcd')
        """
        image_folder = Path(image_folder)
        output_path = Path(output_path)

        # Validate inputs
        images = find_images(image_folder)
        validate_images(images)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Step 1: Run COLMAP SfM pipeline
            self._run_colmap_sfm(image_folder, tmpdir)

            # Step 2: Run COLMAP MVS pipeline
            self._run_colmap_mvs(tmpdir)

            # Step 3: Load and export the point cloud
            self._export_point_cloud(tmpdir, output_path, output_format)

    def _run_colmap_sfm(self, image_folder: Path, workspace: Path):
        """
        Run COLMAP's Structure from Motion (SfM) pipeline.

        Args:
            image_folder: Path to input images
            workspace: Temporary working directory
        """
        db_path = workspace / 'database.db'

        # Feature extraction
        print("Step 1: Feature extraction...")
        subprocess.run([
            'colmap', 'feature_extractor',
            '--database_path', str(db_path),
            '--image_path', str(image_folder),
        ], check=True)

        # Feature matching
        print("Step 2: Feature matching...")
        subprocess.run([
            'colmap', 'exhaustive_matcher',
            '--database_path', str(db_path),
        ], check=True)

        # Reconstruction
        print("Step 3: Running SfM reconstruction...")
        recon_path = workspace / 'sparse'
        recon_path.mkdir(exist_ok=True)

        subprocess.run([
            'colmap', 'mapper',
            '--database_path', str(db_path),
            '--image_path', str(image_folder),
            '--output_path', str(recon_path),
        ], check=True)

    def _run_colmap_mvs(self, workspace: Path):
        """
        Run COLMAP's Multi-View Stereo (MVS) pipeline.

        Args:
            workspace: Temporary working directory containing sparse reconstruction
        """
        print("Step 4: Undistorting images...")
        sparse_path = workspace / 'sparse' / '0'
        dense_path = workspace / 'dense'
        dense_path.mkdir(exist_ok=True)

        subprocess.run([
            'colmap', 'image_undistorter',
            '--image_path', str((workspace.parent / 'images')),  # Placeholder
            '--input_path', str(sparse_path),
            '--output_path', str(dense_path),
        ], check=True, capture_output=True)

        print("Step 5: Dense stereo matching...")
        subprocess.run([
            'colmap', 'patch_match_stereo',
            '--workspace_path', str(dense_path),
        ], check=True)

        print("Step 6: Fusing depth maps...")
        subprocess.run([
            'colmap', 'stereo_fusion',
            '--workspace_path', str(dense_path),
            '--output_path', str(dense_path / 'fused.ply'),
        ], check=True)

    def _export_point_cloud(self, workspace: Path, output_path: Path, format_type: str):
        """
        Load the fused point cloud and export to desired format.

        Args:
            workspace: Temporary working directory
            output_path: Output file path
            format_type: Output format ('obj', 'ply', or 'pcd')
        """
        print(f"Step 7: Exporting to {format_type.upper()}...")

        # Load the fused point cloud
        ply_path = workspace / 'dense' / 'fused.ply'

        if not ply_path.exists():
            raise FileNotFoundError(f"Point cloud not found at {ply_path}")

        pcd = o3d.io.read_point_cloud(str(ply_path))

        # Export in requested format
        if format_type == 'ply':
            o3d.io.write_point_cloud(str(output_path), pcd)
        elif format_type == 'pcd':
            o3d.io.write_point_cloud(str(output_path), pcd)
        elif format_type == 'obj':
            # For OBJ, we need to convert via a mesh (simplified approach)
            # In a real scenario, you might use Poisson reconstruction here
            mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(
                pcd,
                o3d.utility.DoubleVector([0.005, 0.01, 0.02, 0.04])
            )
            o3d.io.write_triangle_mesh(str(output_path), mesh)
