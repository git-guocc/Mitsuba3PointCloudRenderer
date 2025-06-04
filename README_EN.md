<div align="center"><a href="./README.md">中文</a> | English</div>

# [Mitsuba3](https://github.com/mitsuba-renderer/mitsuba3) Point Cloud Renderer

A point cloud visualization tool based on the [Mitsuba3](https://github.com/mitsuba-renderer/mitsuba3) rendering engine, providing high-quality point cloud rendering and animation generation.

## Demo

### Point Cloud Turntable Animation
<div align="center">
  <img src="./examples/output/gif/HelloKitty.gif" width="32%" />
  <img src="./examples/output/gif/Judy.gif" width="32%" />
  <img src="./examples/output/gif/Nick.gif" width="32%" />
</div>

### Example: Rendering without Ground Plane
<div align="center">
  <img src="examples\output\png\elephant_noshadow.png" width="97%" />
</div>

### Example: Rendering with Attached Ground and Shadows
<div align="center">
  <img src="examples\output\png\elephant.png" width="97%" />
</div>

## Features

| Feature | Description |
|------|------|
| Supports multiple point cloud formats | Supports .ply, .npy, .npz, .xyz and other common point cloud files |
| Custom camera parameters and views | Set camera position, orientation, and FOV via CLI or interactive tool |
| Multiple rendering integrators | Supports path (global illumination + shadow), direct (direct lighting) |
| Multiple color modes | Original color, position mapping, height mapping, fixed color |
| Point count control | Specify number of points to render, suitable for large-scale point clouds |
| Optional ground and area light | Choose whether to include ground plane and area light |
| Batch rendering | Render multiple point cloud files in batch |
| Mesh sampling tool | Sample point clouds from OBJ/STL mesh surfaces |
| Add noise to point clouds | Tool to add Gaussian noise to point clouds |
| Interactive camera setup | Adjust camera interactively with Open3D window |
| Point cloud turntable GIF | Generate turntable animation GIF with one click |

## Environment Setup

### Recommended: Using Conda Environment

1. Clone the repository:

    ```bash
    git clone https://github.com/yourusername/Mitsuba3PointCloudRenderer.git
    cd Mitsuba3PointCloudRenderer
    ```

2. Create and activate the Conda environment:

    ```bash
    conda env create -f environment.yml
    conda activate PointCloudRender
    ```

3. **Ensure Mitsuba3 is installed**  
   This tool will automatically search for the Mitsuba3 executable (supports PATH, environment variables, and common install paths), no need to set environment variables manually.  
   Just make sure Mitsuba3 is installed and can be called via `mitsuba --version` in the command line.

   To manually specify the Mitsuba3 path, set the environment variable `MITSUBA_EXECUTABLE`:

   - **Windows (CMD)**
     ```cmd
     set MITSUBA_EXECUTABLE=C:\path\to\mitsuba.exe
     ```
   - **Windows (PowerShell)**
     ```powershell
     $env:MITSUBA_EXECUTABLE = "C:\path\to\mitsuba.exe"
     ```
   - **Linux/macOS**
     ```bash
     export MITSUBA_EXECUTABLE=/path/to/mitsuba
     ```

   Or **add your Mitsuba path directly to the `common_paths` list in `mitsuba_pcr/render.py`**; the code will prioritize these paths.

### Dependencies

- Python
- Mitsuba3 (install separately)
- NumPy
- Open3D
- Pillow
- Other dependencies: scipy (for turntable animation), imageio (for GIF generation), tqdm (optional, for progress bar)

## Usage

### Render a single point cloud

```bash
python render_point_cloud.py examples\data\pcl\HelloKitty.ply --output_dir renders --integrator path --samples 256
```

### Batch rendering

```bash
python render_point_cloud.py input_directory --batch --pattern "*.ply" --output_dir renders
```

### Interactive camera setup tool

```bash
python tools/camera_setup.py examples\data\pcl\HelloKitty.ply
```

Adjust the view in the pop-up window, and the camera parameters will be displayed after closing the window.

### Sample point cloud from mesh

```bash
python tools/sample_mesh.py input.obj --num_points 100000 --output_file output.ply
```

### Add noise to point cloud

```bash
python tools/add_noise.py examples\data\pcl\HelloKitty.ply --noise_std 0.01 --output_file noisy.ply
```

### Generate point cloud turntable GIF

```bash
# Generate turntable GIF with default parameters
python tools/create_turntable_gif.py examples\data\pcl\HelloKitty.ply --output_gif output\animation.gif

# Generate turntable GIF with custom camera parameters
python tools/create_turntable_gif.py examples\data\pcl\HelloKitty.ply --output_gif output\animation.gif --camera_params "0,0,2 0,0,0 0,1,0" --fov 45 --rotation_axis initial_up --frames 36

# Generate turntable GIF with world axis rotation
python tools/create_turntable_gif.py examples\data\pcl\HelloKitty.ply --output_gif output\animation.gif --rotation_axis z --camera_distance 2.0 --camera_elevation_deg 15.0 --frames 72
```

### Generate turntable GIF after using interactive camera setup

```bash
# 1. First use the interactive tool to get the ideal camera parameters
python tools/camera_setup.py examples\data\pcl\HelloKitty.ply
# Output example: --camera_params "-0.5,0.8,1.2 0,0,0" --fov 60

# 2. Use the obtained camera parameters to generate a high-quality turntable GIF
python tools/create_turntable_gif.py examples\data\pcl\HelloKitty.ply --output_gif output\turntable.gif --camera_params "-0.5,0.8,1.2 0,0,0" --fov 60 --rotation_axis initial_up --frames 72 --samples 128 --resolution 1920 1080 --point_radius 0.015
```

### Batch render multiple point cloud files

```bash
python tools/batch_render.py --base_dir dataset --methods_dirs method1 method2 method3 --target_cloud points.ply --output_dir renders --integrator direct --samples 256
```

## Command Line Arguments

### render_point_cloud.py

```
usage: render_point_cloud.py [-h] [--output_dir OUTPUT_DIR] [--output_prefix OUTPUT_PREFIX]
                            [--output_format {png,jpg,exr}] [--batch] [--pattern PATTERN]
                            [--integrator {path,direct}] [--samples SAMPLES] [--max_depth MAX_DEPTH]
                            [--num_points NUM_POINTS] [--point_radius POINT_RADIUS]
                            [--resolution WIDTH HEIGHT]
                            [--color_mode {original,position,height,fixed}]
                            [--fixed_color R G B] [--color_axis {0,1,2}]
                            [--color_map {viridis,jet,rainbow,turbo}]
                            [--camera_params CAMERA_PARAMS] [--fov FOV]
                            [--flip_horizontal | --no_flip_horizontal]
                            [--include_ground | --no_ground]
                            [--include_area_light | --no_area_light]
                            [--attach_ground] [--attached_ground_offset ATTACHED_GROUND_OFFSET]
                            [--attached_ground_size ATTACHED_GROUND_SIZE]
                            [--env_light_intensity ENV_LIGHT_INTENSITY]
                            [--background_color BG_R BG_G BG_B]
                            [--area_light_intensity AREA_LIGHT_INTENSITY]
                            [--seed SEED] [--cleanup] [--mitsuba_path MITSUBA_PATH]
                            input_file
```

**Note on Scene and Lighting Parameters:**

*   `--include_ground` / `--no_ground`: Controls whether to include a fixed standard ground plane.
*   `--attach_ground`: Adds a ground plane attached beneath the point cloud, which rotates with the camera view. Ideal for scenarios requiring object rotation while maintaining relative ground position. Enabling this option automatically disables the standard ground (`--include_ground` will be set to `False`).
    *   `--attached_ground_offset FLOAT`: Offset of the attached plane relative to the lowest point of the point cloud's projection in that direction (default: -0.05).
    *   `--attached_ground_size FLOAT`: Size of the attached plane (default: 15).
*   `--include_area_light` / `--no_area_light`: Controls whether to include a main area light.
*   `--background_color R G B`: Defines the background color (e.g., `1 1 1` for white), range [0, 1]. This color value directly sets the radiance of the scene's sole environment emitter (the background sky). Thus, it serves as both the directly visible background color and the primary source of global ambient light.
*   `--area_light_intensity FLOAT`: Controls the intensity of the main area light (default: 3.0). This is the primary directional light source in the scene, responsible for casting major shadows on the point cloud and ground. Please note: The size of the area light is currently fixed in the code and cannot be modified via this command-line argument.
*   `--env_light_intensity FLOAT`: Ambient light intensity (range 0-1, default: 1.0). **[Current Status]** This parameter is intended to control an independent ambient fill light to soften shadows. However, as Mitsuba scenes currently support only a single environment emitter (whose properties are already defined by `--background_color`), this parameter's value is not activated in the current scene generation logic to add an additional, separate light source. To adjust the overall ambient lighting level, you should primarily control the brightness of the background emitter via `--background_color`.

### tools/camera_setup.py

```
usage: camera_setup.py [-h] [--initial_params INITIAL_PARAMS] input_file
```

### tools/batch_render.py

```
usage: batch_render.py [-h] --base_dir BASE_DIR [--methods_dirs METHODS_DIRS [METHODS_DIRS ...]]
                      [--target_cloud TARGET_CLOUD] [--pattern PATTERN]
                      [--output_dir OUTPUT_DIR] [--integrator {path,direct}]
                      [--samples SAMPLES] [--num_points NUM_POINTS]
                      [--point_radius POINT_RADIUS]
                      [--color_mode {original,position,height,fixed}]
                      [--camera_params CAMERA_PARAMS] [--seed SEED] [--cleanup]
                      [--mitsuba_path MITSUBA_PATH]
```

### tools/sample_mesh.py

```
usage: sample_mesh.py [-h] [--num_points NUM_POINTS] [--output_file OUTPUT_FILE]
                     [--seed SEED]
                     input_file
```

### tools/add_noise.py

```
usage: add_noise.py [-h] [--noise_std NOISE_STD] [--output_file OUTPUT_FILE]
                   [--seed SEED]
                   input_file
```

### tools/create_turntable_gif.py

```
usage: create_turntable_gif.py [-h] [--output_gif OUTPUT_GIF] [--frames FRAMES]
                               [--duration DURATION] [--rotation_axis {x,y,z,initial_up}]
                               [--clockwise] [--camera_distance CAMERA_DISTANCE]
                               [--camera_elevation_deg CAMERA_ELEVATION_DEG]
                               [--start_angle_offset_deg START_ANGLE_OFFSET_DEG]
                               [--camera_params CAMERA_PARAMS] [--fov FOV]
                               [--resolution RESOLUTION RESOLUTION] [--samples SAMPLES]
                               [--point_radius POINT_RADIUS]
                               [--color_mode {original,position,height,fixed}]
                               [--fixed_color FIXED_COLOR FIXED_COLOR FIXED_COLOR]
                               [--color_axis {0,1,2}] [--color_map {viridis,jet,rainbow,turbo}]
                               [--num_render_points NUM_RENDER_POINTS]
                               [--temp_dir_frames TEMP_DIR_FRAMES] [--mitsuba_path MITSUBA_PATH]
                               [--keep_frames] [--render_script_path RENDER_SCRIPT_PATH]
                               input_file
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 