"""Core photogrammetry processing pipeline using pycolmap."""

import subprocess
import tempfile
from pathlib import Path
from typing import Optional
import numpy as np
import open3d as o3d
import pycolmap
from .utils import find_images, validate_images


class PhotogrammetryProcessor:
    """Orchestrates the photogrammetry pipeline using pycolmap and COLMAP."""

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
        elif self.quality == 'medium':
            self.max_image_size = 2048
        else:  # high
            self.max_image_size = 4096

    def process(self, image_folder: Path, output_path: Path, output_format: str = 'obj'):
        """
        Run the complete photogrammetry pipeline.

        Args:
            image_folder: Path to folder containing JPEG images
            output_path: Path for output 3D model
            output_format: Output format ('obj', 'ply', or 'pcd')
        """
        image_folder = Path(image_folder).resolve()
        output_path = Path(output_path).resolve()

        # Validate inputs
        images = find_images(image_folder)
        validate_images(images)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            db_path = tmpdir / 'database.db'
            sparse_path = tmpdir / 'sparse'
            sparse_path.mkdir(exist_ok=True)

            # Step 1-3: Run COLMAP SfM pipeline via pycolmap
            self._run_colmap_sfm(image_folder, db_path, sparse_path)

            # Step 4-6: Run dense reconstruction (may use subprocess for MVS)
            pcd = self._run_dense_reconstruction(image_folder, sparse_path, tmpdir)

            # Step 7: Export the point cloud
            self._export_point_cloud(pcd, output_path, output_format)

    def _run_colmap_sfm(self, image_folder: Path, db_path: Path, sparse_path: Path):
        """
        Run COLMAP's Structure from Motion (SfM) pipeline using pycolmap.

        Args:
            image_folder: Path to input images
            db_path: Database path for COLMAP
            sparse_path: Output path for sparse reconstruction
        """
        print("Step 1-3: Running SfM reconstruction (feature extraction → matching → mapping)...")

        image_folder = str(image_folder)
        db_path = str(db_path)
        sparse_path = str(sparse_path)

        # Create empty database first
        db = pycolmap.Database.open(db_path)
        db.close()

        # Import images (takes database path, not Database object)
        print("  - Importing images...")
        pycolmap.import_images(
            db_path,
            image_folder,
            camera_mode=pycolmap.CameraMode.AUTO,
        )

        # Extract features
        print("  - Extracting features...")
        feat_extractor_options = pycolmap.FeatureExtractionOptions()
        feat_extractor_options.use_gpu = False
        feat_extractor_options.max_image_size = self.max_image_size
        pycolmap.extract_features(db_path, image_folder, extraction_options=feat_extractor_options)

        # Match features
        print("  - Matching features...")
        matcher_options = pycolmap.FeatureMatchingOptions()
        pycolmap.match_exhaustive(db_path, matching_options=matcher_options)

        # Geometric verification
        print("  - Geometric verification...")
        geometric_options = pycolmap.GeometricVerifierOptions()
        pycolmap.geometric_verification(db_path, verifier_options=geometric_options)

        # Incremental mapping
        print("  - Running incremental mapping...")
        mapper_options = pycolmap.IncrementalPipelineOptions()
        maps = pycolmap.incremental_mapping(db_path, image_folder, sparse_path, mapper_options)

    def _run_dense_reconstruction(self, image_folder: Path, sparse_path: Path, tmpdir: Path):
        """
        Run dense reconstruction using COLMAP's MVS pipeline.
        Falls back to Open3D densification if needed.

        Args:
            image_folder: Path to input images
            sparse_path: Path to sparse reconstruction
            tmpdir: Temporary working directory

        Returns:
            Open3D PointCloud object
        """
        print("Step 4-6: Running dense reconstruction...")

        dense_path = tmpdir / 'dense'
        dense_path.mkdir(exist_ok=True)

        try:
            # Try to undistort and run MVS via subprocess (pycolmap doesn't fully cover this)
            sparse_recon_path = sparse_path / '0'
            if sparse_recon_path.exists():
                self._run_mvs_pipeline(image_folder, sparse_recon_path, dense_path)
                ply_path = dense_path / 'fused.ply'
                if ply_path.exists():
                    return o3d.io.read_point_cloud(str(ply_path))
        except Exception as e:
            print(f"Dense MVS pipeline failed ({e}), falling back to sparse cloud...")

        # Fallback: extract sparse points from the reconstruction
        return self._load_sparse_points(sparse_path)

    def _run_mvs_pipeline(self, image_folder: Path, sparse_path: Path, dense_path: Path):
        """
        Run COLMAP's MVS pipeline via subprocess.

        Args:
            image_folder: Path to input images
            sparse_path: Path to sparse reconstruction
            dense_path: Output path for dense reconstruction
        """
        # Undistort images
        print("  - Undistorting images...")
        subprocess.run([
            'colmap', 'image_undistorter',
            '--image_path', str(image_folder),
            '--input_path', str(sparse_path),
            '--output_path', str(dense_path),
        ], check=True, capture_output=True)

        # Patch match stereo
        print("  - Dense stereo matching...")
        subprocess.run([
            'colmap', 'patch_match_stereo',
            '--workspace_path', str(dense_path),
        ], check=True, capture_output=True)

        # Stereo fusion
        print("  - Fusing depth maps...")
        subprocess.run([
            'colmap', 'stereo_fusion',
            '--workspace_path', str(dense_path),
            '--output_path', str(dense_path / 'fused.ply'),
        ], check=True, capture_output=True)

    def _load_sparse_points(self, sparse_path: Path) -> o3d.geometry.PointCloud:
        """
        Load sparse points from COLMAP reconstruction.

        Args:
            sparse_path: Path to sparse reconstruction

        Returns:
            Open3D PointCloud object
        """
        print("  - Loading sparse point cloud...")
        recon_path = sparse_path / '0'

        if not recon_path.exists():
            raise FileNotFoundError(f"No reconstruction found at {recon_path}")

        reconstruction = pycolmap.Reconstruction(str(recon_path))

        # Extract 3D points
        points_3d = []
        colors = []

        for point3d in reconstruction.points3D.values():
            points_3d.append(point3d.xyz)
            colors.append(point3d.color / 255.0)  # Normalize to [0, 1]

        if not points_3d:
            raise ValueError("No 3D points found in reconstruction")

        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(np.array(points_3d))
        pcd.colors = o3d.utility.Vector3dVector(np.array(colors))

        return pcd

    def _export_point_cloud(self, pcd: o3d.geometry.PointCloud, output_path: Path, format_type: str):
        """
        Export point cloud to desired format.

        Args:
            pcd: Open3D PointCloud object
            output_path: Output file path
            format_type: Output format ('obj', 'ply', or 'pcd')
        """
        print(f"Step 7: Exporting to {format_type.upper()}...")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format_type == 'ply':
            o3d.io.write_point_cloud(str(output_path), pcd)
        elif format_type == 'pcd':
            o3d.io.write_point_cloud(str(output_path), pcd)
        elif format_type == 'obj':
            # For OBJ, use Poisson surface reconstruction for proper mesh
            print("  - Estimating normals...")
            if not pcd.has_normals():
                pcd.estimate_normals()

            print("  - Poisson surface reconstruction...")
            mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
                pcd, depth=9
            )

            # Remove low-density vertices (outliers)
            vertices_to_remove = densities < np.quantile(densities, 0.1)
            mesh.remove_vertices_by_mask(vertices_to_remove)

            o3d.io.write_triangle_mesh(str(output_path), mesh)
            print(f"  - Mesh created with {len(mesh.vertices)} vertices and {len(mesh.triangles)} triangles")
