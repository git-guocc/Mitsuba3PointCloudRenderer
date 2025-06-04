<div align="center">中文 | <a href="./README_EN.md">English</a></div>

# [Mitsuba3](https://github.com/mitsuba-renderer/mitsuba3) 点云渲染器

一个基于[Mitsuba3](https://github.com/mitsuba-renderer/mitsuba3)渲染引擎的点云可视化工具，提供高质量的点云渲染和动画生成功能。

## 效果展示

### 点云转盘动画效果
<div align="center">
  <img src="./examples/output/gif/HelloKitty.gif" width="32%" />
  <img src="./examples/output/gif/Judy.gif" width="32%" />
  <img src="./examples/output/gif/Nick.gif" width="32%" />
</div>

### 效果示例：无地面渲染
<div align="center">
  <img src="examples\output\png\elephant_noshadow.png" width="97%" />
</div>

### 效果示例：带贴附地面与阴影渲染
<div align="center">
  <img src="examples\output\png\elephant.png" width="97%" />
</div>

## 功能特点

- 支持多种点云格式（.ply, .npy, .npz, .xyz）
- 支持自定义相机参数和视角
- 支持多种渲染积分器（path、direct）
- 支持多种颜色模式（原始颜色、位置映射、高度映射、固定颜色）
- 支持控制渲染点数量，可处理大规模点云
- 可选择是否包含地面平面和环境光照
- 支持批量渲染多个点云文件
- 提供网格采样工具，可从OBJ/STL模型生成点云
- 提供点云添加噪声的工具
- 交互式相机设置工具
- 支持生成点云转盘动画GIF

## 环境配置

### 推荐方式：使用 Conda 环境

1. 克隆仓库：

    ```bash
    git clone https://github.com/yourusername/Mitsuba3PointCloudRenderer.git
    cd Mitsuba3PointCloudRenderer
    ```

2. 创建并激活 Conda 环境：

    ```bash
    conda env create -f environment.yml
    conda activate PointCloudRender
    ```

3. **确保 Mitsuba3 已安装**  
   本工具会自动查找 Mitsuba3 可执行文件（支持 PATH、环境变量和常见安装路径），无需手动设置环境变量。  
   你只需保证 Mitsuba3 已正确安装，并可在命令行中通过 `mitsuba --version` 正常调用即可。

   如需手动指定 Mitsuba3 路径，可设置环境变量 `MITSUBA_EXECUTABLE`：

   - **Windows（CMD）**
     ```cmd
     set MITSUBA_EXECUTABLE=C:\path\to\mitsuba.exe
     ```
   - **Windows（PowerShell）**
     ```powershell
     $env:MITSUBA_EXECUTABLE = "C:\path\to\mitsuba.exe"
     ```
   - **Linux/macOS**
     ```bash
     export MITSUBA_EXECUTABLE=/path/to/mitsuba
     ```

   或者**直接在 `mitsuba_pcr/render.py` 的 `common_paths` 列表中添加你的 Mitsuba 路径**，代码会自动优先查找这些路径。

### 依赖项

- Python
- Mitsuba3（需要单独安装）
- NumPy
- Open3D
- Pillow
- 其他依赖：scipy (用于转盘动画)、imageio (用于GIF生成)、tqdm (可选，用于进度条显示)

## 使用方法

### 渲染单个点云

```bash
python render_point_cloud.py examples\data\pcl\HelloKitty.ply --output_dir renders --integrator path --samples 256
```

### 批量渲染

```bash
python render_point_cloud.py input_directory --batch --pattern "*.ply" --output_dir renders
```

### 使用交互式相机设置工具

```bash
python tools/camera_setup.py examples\data\pcl\HelloKitty.ply
```

然后在弹出的窗口中调整视角，关闭窗口后会显示相机参数。

### 从网格采样点云

```bash
python tools/sample_mesh.py input.obj --num_points 100000 --output_file output.ply
```

### 为点云添加噪声

```bash
python tools/add_noise.py examples\data\pcl\HelloKitty.ply --noise_std 0.01 --output_file noisy.ply
```

### 生成点云转盘动画GIF

```bash
# 使用默认参数生成转盘GIF
python tools/create_turntable_gif.py examples\data\pcl\HelloKitty.ply --output_gif output\animation.gif

# 使用自定义相机参数生成转盘GIF
python tools/create_turntable_gif.py examples\data\pcl\HelloKitty.ply --output_gif output\animation.gif --camera_params "0,0,2 0,0,0 0,1,0" --fov 45 --rotation_axis initial_up --frames 36

# 使用世界轴旋转生成转盘GIF
python tools/create_turntable_gif.py examples\data\pcl\HelloKitty.ply --output_gif output\animation.gif --rotation_axis z --camera_distance 2.0 --camera_elevation_deg 15.0 --frames 72
```

### 使用交互式相机设置工具后生成转盘GIF

```bash
# 1. 首先使用交互式工具获取理想的相机参数
python tools/camera_setup.py examples\data\pcl\HelloKitty.ply
# 输出示例: --camera_params "-0.5,0.8,1.2 0,0,0" --fov 60

# 2. 使用获取的相机参数生成高质量转盘GIF
python tools/create_turntable_gif.py examples\data\pcl\HelloKitty.ply --output_gif output\turntable.gif --camera_params "-0.5,0.8,1.2 0,0,0" --fov 60 --rotation_axis initial_up --frames 72 --samples 128 --resolution 1920 1080 --point_radius 0.015
```

### 批量渲染多个点云文件

```bash
python tools/batch_render.py --base_dir dataset --methods_dirs method1 method2 method3 --target_cloud points.ply --output_dir renders --integrator direct --samples 256
```

## 命令行参数

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

**关于场景与光照参数的说明：**

*   `--include_ground` / `--no_ground`: 控制是否包含一个固定的标准地面平面。
*   `--attach_ground`: 添加一个贴附在点云下方的平面，该平面会跟随相机视角旋转，适用于需要旋转物体同时保持地面相对位置的场景。启用此选项会自动禁用标准地面 (`--include_ground` 将被设为 `False`)。
    *   `--attached_ground_offset FLOAT`: 贴附平面相对于点云在该方向上投影的最低点的偏移量（默认为-0.05）。
    *   `--attached_ground_size FLOAT`: 贴附平面的大小（默认为15）。
*   `--include_area_light` / `--no_area_light`: 控制是否包含一个主要的面光源。
*   `--background_color R G B`: 定义背景颜色（例如 `1 1 1` 表示白色），范围 [0, 1]。此颜色值直接设定了场景中唯一环境发射器（背景天空）的辐射亮度。因此，它既是直接可见的背景颜色，也是场景全局环境光的主要来源。
*   `--area_light_intensity FLOAT`: 控制主要面光源的强度（默认为3.0）。这是场景中的主要方向性光源，负责产生点云和地面上的主要阴影。请注意：面光源的大小当前在代码中固定，无法通过此命令行参数修改。
*   `--env_light_intensity FLOAT`: 环境光强度（范围 0-1，默认为1.0）。**[当前状态]** 此参数的预期功能是控制一个独立的环境补光，用以柔化阴影。但由于Mitsuba场景目前仅支持单个环境发射器（该发射器已由 `--background_color` 定义其属性），此参数值在当前的场景生成逻辑中未被激活以添加额外的独立光源。如需调整整体环境光照水平，应主要通过 `--background_color` 来控制背景发射器的亮度。

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

## 许可证

本项目使用 MIT 许可证 - 详情请参见 [LICENSE](LICENSE) 文件。



