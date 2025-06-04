#!/usr/bin/env python
"""
工具脚本：为点云创建转盘动画 GIF

通过围绕点云旋转相机并使用 Mitsuba2 进行渲染来生成一系列帧，
然后将这些帧合成为一个动画 GIF。
"""

import argparse
import glob
# import imageio # Defer import to main to check for availability
import math
import os
import shutil
import subprocess
import sys
import numpy as np # 新增导入
import re # 新增导入: 正则表达式模块

# SciPy是可选的，仅在 rotation_axis == 'initial_up' 时需要
SCIPY_AVAILABLE = False
try:
    from scipy.spatial.transform import Rotation
    SCIPY_AVAILABLE = True
except ImportError:
    pass # SciPy不可用，如果用户选择相应功能则报错

# TQDM是可选的，用于进度条显示
TQDM_AVAILABLE = False
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    pass

# 用于从字符串中提取数字的正则表达式模式
FLOAT_PATTERN = r"[-+]?\d*\.?\d+"

def get_default_render_script_path():
    """获取 render_point_cloud.py 脚本的默认路径"""
    # C:\Users\cug\Desktop\GitHub\PointGui\Mitsuba2PointCloudRenderer\tools\create_turntable_gif.py
    # C:\Users\cug\Desktop\GitHub\PointGui\Mitsuba2PointCloudRenderer\render_point_cloud.py
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(script_dir, "..", "render_point_cloud.py"))

def normalize(v):
    norm = np.linalg.norm(v)
    if norm == 0:
        return v
    return v / norm

def _derive_orbital_params_from_user_view(params_string, current_rotation_axis, current_fov):
    """根据用户提供的相机参数字符串推导轨道相机参数"""
    try:
        numbers_found = re.findall(FLOAT_PATTERN, params_string)
        if len(numbers_found) != 9:
            raise ValueError(f"预期找到9个数字，但从 '{params_string}' 中解析出 {len(numbers_found)} 个。")
        
        parts = [float(n_str) for n_str in numbers_found]

    except ValueError as e:
        print(f"错误: 处理相机参数字符串时出错: {e}")
        print(f"  提供的参数值为: \"{params_string}\"")
        print(f"  期望格式为9个数字，例如: \"ox oy oz tx ty tz ux uy uz\" (可混用逗号/空格)")
        return None

    user_origin = np.array(parts[0:3])
    user_target = np.array(parts[3:6])
    # user_up = np.array(parts[6:9]) # user_up 主要用于确定方向，GIF的up由轨道逻辑决定

    # GIF脚本的目标点固定为(0,0,0)
    gif_render_target = np.array([0.0, 0.0, 0.0])

    # 计算从用户相机位置指向用户目标点的向量
    view_vector_user_to_target = user_target - user_origin
    if np.linalg.norm(view_vector_user_to_target) < 1e-6:
        print("警告: 用户提供的相机原点和目标点几乎重合。")
        return None

    # 新的相机位置，使得 new_pos -> gif_render_target 与 user_origin -> user_target 向量相同
    gif_orbit_start_origin = gif_render_target - view_vector_user_to_target

    calculated_distance = np.linalg.norm(gif_orbit_start_origin)
    if calculated_distance < 1e-6:
        print("警告: 推导出的相机与目标点(0,0,0)的距离过近。")
        return None

    calculated_elevation_deg = 0.0
    calculated_start_angle_deg = 0.0

    if current_rotation_axis == 'z':
        val_for_asin = gif_orbit_start_origin[2] / calculated_distance
        calculated_elevation_rad = np.arcsin(np.clip(val_for_asin, -1.0, 1.0))
        calculated_elevation_deg = np.degrees(calculated_elevation_rad)
        calculated_start_angle_rad = np.arctan2(gif_orbit_start_origin[1], gif_orbit_start_origin[0])
        calculated_start_angle_deg = np.degrees(calculated_start_angle_rad)
    elif current_rotation_axis == 'y':
        val_for_asin = gif_orbit_start_origin[1] / calculated_distance
        calculated_elevation_rad = np.arcsin(np.clip(val_for_asin, -1.0, 1.0))
        calculated_elevation_deg = np.degrees(calculated_elevation_rad)
        calculated_start_angle_rad = np.arctan2(gif_orbit_start_origin[0], gif_orbit_start_origin[2])
        calculated_start_angle_deg = np.degrees(calculated_start_angle_rad)
    elif current_rotation_axis == 'x':
        val_for_asin = gif_orbit_start_origin[0] / calculated_distance
        calculated_elevation_rad = np.arcsin(np.clip(val_for_asin, -1.0, 1.0))
        calculated_elevation_deg = np.degrees(calculated_elevation_rad)
        calculated_start_angle_rad = np.arctan2(gif_orbit_start_origin[2], gif_orbit_start_origin[1])
        calculated_start_angle_deg = np.degrees(calculated_start_angle_rad)
    else:
        # Should not happen if called correctly for world axes
        print(f"错误: 未知的世界旋转轴 '{current_rotation_axis}' 用于参数推导。")
        return None

    print("信息: 根据 --set_start_from_mitsuba_params 为世界轴旋转推导出的轨道参数:")
    print(f"  - camera_distance: {calculated_distance:.4f}")
    print(f"  - camera_elevation_deg: {calculated_elevation_deg:.2f} (用于旋转轴 '{current_rotation_axis}')")
    print(f"  - start_angle_offset_deg: {calculated_start_angle_deg:.2f} (用于旋转轴 '{current_rotation_axis}')")
    print(f"  - fov (来自命令行): {current_fov:.2f}")
    print("注意: 原始up向量的倾斜效果可能不会完全保留在GIF动画中。")

    return calculated_distance, calculated_elevation_deg, calculated_start_angle_deg

def main():
    parser = argparse.ArgumentParser(description="使用Mitsuba2为点云创建转盘GIF。")
    
    # 输入/输出参数
    parser.add_argument("input_file", help="输入点云文件路径 (.ply, .npy, .npz)")
    parser.add_argument("--output_gif", default="examples/output/gif/turntable.gif", help="输出GIF文件路径 (默认: turntable.gif)")
    
    # GIF 和动画参数
    parser.add_argument("--frames", type=int, default=36, help="360度旋转的总帧数 (默认: 36)")
    parser.add_argument("--duration", type=float, default=0.1, help="GIF中每帧的持续时间（秒） (默认: 0.1)")
    parser.add_argument("--rotation_axis", choices=['x', 'y', 'z', 'initial_up'], default='z', help="旋转轴: x, y, z (世界轴), 或 initial_up (基于提供的初始视图的up向量进行旋转，需配合--set_start_from_mitsuba_params)")
    parser.add_argument("--clockwise", action="store_true", help="顺时针旋转 (默认: 逆时针)")
    
    # 轨道相机参数组
    orbital_group = parser.add_argument_group('轨道相机参数 (当 rotation_axis 为 x, y, 或 z 时使用)')
    orbital_group.add_argument("--camera_distance", type=float, default=2.0, 
                        help="相机距离点云中心点的距离 (点云归一化后) (默认: 2.0)")
    orbital_group.add_argument("--camera_elevation_deg", type=float, default=15.0,
                        help="相机俯仰角（度），相对于旋转平面。 (默认: 15.0)")
    orbital_group.add_argument("--start_angle_offset_deg", type=float, default=0.0, 
                        help="旋转动画的起始角度偏移（度） (默认: 0.0)")

    # 从Mitsuba参数设定起始视角参数组
    direct_start_group = parser.add_argument_group('从现有视图设定起始参数 (实验性)')
    direct_start_group.add_argument("--camera_params", type=str, default=None,
                        help='可选：提供Mitsuba的相机参数字符串 "origin_x,origin_y,origin_z target_x,target_y,target_z up_x,up_y,up_z" (9个数字) 以此设定动画起始点。将覆盖轨道相机参数。FOV仍需单独指定。例: "0,0,3 0,0,0 0,1,0"')

    parser.add_argument("--fov", type=float, default=45, help="相机视场角 (度) (默认: 45)")

    # 渲染参数 (从 render_point_cloud.py 借鉴并设置适合GIF的默认值)
    parser.add_argument("--resolution", nargs=2, type=int, default=[800, 600], help="输出分辨率 (宽 高) (默认: [800, 600])")
    parser.add_argument("--samples", type=int, default=64, help="每像素采样数 (默认: 64, 较低以提高速度)")
    parser.add_argument("--point_radius", type=float, default=0.015, help="点半径 (默认: 0.015)")
    parser.add_argument("--attach_ground", action="store_true", help="添加贴附在点云下方的平面（适用于旋转视角）")
    parser.add_argument("--attached_ground_offset", type=float, default=-0.05, help="贴附平面相对于点云最低点的偏移量")
    parser.add_argument("--attached_ground_size", type=float, default=15, help="贴附平面的大小")
    parser.add_argument("--env_light_intensity", type=float, default=0.5, help="环境光强度（0-1），用于均匀背景照明")
    parser.add_argument("--background_color", nargs=3, type=float, default=[1, 1, 1], 
                        help="背景颜色 (R G B)，范围[0, 1]")
    parser.add_argument("--color_mode", choices=["original", "position", "height", "fixed"], default="original", 
                        help="颜色模式 (默认: original)")
    parser.add_argument("--fixed_color", nargs=3, type=float, default=[0.7, 0.7, 0.7], 
                        help="固定颜色 (R G B)，当color_mode为'fixed'时使用")
    parser.add_argument("--color_axis", type=int, choices=[0, 1, 2], default=2, 
                        help="用于'height'颜色模式的坐标轴 (0=X, 1=Y, 2=Z)")
    parser.add_argument("--color_map", choices=["viridis", "jet", "rainbow", "turbo"], default="viridis", 
                        help="用于'height'颜色模式的颜色映射")
    
    parser.add_argument("--num_render_points", type=int, default=-1,
                        help="渲染时使用的点数 (-1 表示使用全部点) (默认: -1)")

    # 其他参数
    parser.add_argument("--temp_dir_frames", default="temp_turntable_frames", 
                        help="存储中间帧的临时目录 (默认: temp_turntable_frames)")
    parser.add_argument("--mitsuba_path", help="Mitsuba可执行文件路径 (例如 mitsuba.exe)")
    parser.add_argument("--keep_frames", action="store_true", help="GIF创建后保留中间帧图像")
    parser.add_argument("--render_script_path", default=get_default_render_script_path(),
                        help=f"render_point_cloud.py脚本的路径 (默认: {get_default_render_script_path()})")

    args = parser.parse_args()

    if args.rotation_axis == 'initial_up' and not args.camera_params:
        print("错误: 当 rotation_axis='initial_up' 时, 必须提供 --camera_params。")
        return 1
    if args.rotation_axis == 'initial_up' and not SCIPY_AVAILABLE:
        print("错误: 当 rotation_axis='initial_up' 时, 需要安装 scipy 库 (pip install scipy)。")
        return 1
    
    initial_user_origin_np, initial_user_target_np, initial_user_up_np = None, None, None
    # 当使用 initial_up 旋转时，这些参数将直接使用，而不是转换轨道参数
    # 当使用世界轴旋转且提供了 camera_params 时，轨道参数会被覆盖

    if args.camera_params:
        try:
            numbers_found = re.findall(FLOAT_PATTERN, args.camera_params)
            if len(numbers_found) != 9:
                raise ValueError(f"预期找到9个数字，但从 '{args.camera_params}' 中解析出 {len(numbers_found)} 个。")

            parts = [float(n_str) for n_str in numbers_found]
            
            initial_user_origin_np = np.array(parts[0:3])
            initial_user_target_np = np.array(parts[3:6])
            initial_user_up_np = normalize(np.array(parts[6:9])) # 确保up向量是单位向量
        except ValueError as e:
            print(f"错误: 解析 --camera_params 失败: {e}")
            print(f"  提供的参数值为: \"{args.camera_params}\"")
            return 1

        if args.rotation_axis in ['x', 'y', 'z']:
            derived_params = _derive_orbital_params_from_user_view(args.camera_params, args.rotation_axis, args.fov)
            if derived_params:
                args.camera_distance, args.camera_elevation_deg, args.start_angle_offset_deg = derived_params
                print(f"信息: 已使用推导出的轨道参数: dist={args.camera_distance:.2f}, elev={args.camera_elevation_deg:.2f}, start_angle={args.start_angle_offset_deg:.2f}")
            else:
                print("警告: 无法从用户参数推导轨道参数，将使用默认或指定的轨道参数。")
        # 如果是 initial_up, 则不转换，直接使用 initial_user_origin_np 等

    if not os.path.exists(args.input_file):
        print(f"错误: 输入文件未找到: {args.input_file}")
        return 1
    
    if not os.path.exists(args.render_script_path):
        print(f"错误: 渲染脚本未找到: {args.render_script_path}")
        print("请使用 --render_script_path 指定其位置。")
        return 1

    # 检查 imageio 是否安装
    try:
        import imageio.v2 as iio
    except ImportError:
        print("错误: imageio库未安装或版本过旧。请运行 'pip install imageio'。")
        print("或者尝试: python -m pip install imageio")
        return 1

    # 创建或清理临时帧目录
    if os.path.exists(args.temp_dir_frames):
        print(f"正在清理已存在的临时目录: {args.temp_dir_frames}")
        shutil.rmtree(args.temp_dir_frames)
    os.makedirs(args.temp_dir_frames, exist_ok=True)

    print(f"将为转盘动画生成 {args.frames} 帧...")
    if args.rotation_axis != 'initial_up':
        print(f"使用轨道参数: 距离={args.camera_distance:.2f}, 仰角={args.camera_elevation_deg:.2f}, 起始偏移={args.start_angle_offset_deg:.2f}, 旋转轴='{args.rotation_axis}'")
    else:
        print(f"使用初始视图参数进行旋转: 轴方向=initial_up (来自用户输入), 旋转中心=initial_target (来自用户输入)")
    
    frame_files = []
    
    # --- 为 initial_up 模式预计算 --- 
    actual_rotation_axis_np = None
    vec_to_rotate_np = None
    rotation_center_np = np.array([0.0,0.0,0.0]) # 默认渲染目标
    true_initial_camera_up_for_rotation = None

    if args.rotation_axis == 'initial_up' and initial_user_origin_np is not None:
        # 在 initial_up 模式下，我们总是以用户提供的 target 为旋转中心
        # 并且渲染时，点云会被移到(0,0,0), 所以相机也需要相对移动
        # 关键是保持 origin_user -> target_user 这个向量，然后旋转 origin_user
        
        # 1. 真正的旋转中心是用户提供的 target
        rotation_center_np = initial_user_target_np 
        
        # 2. 旋转轴是用户提供的 up 向量方向 (已归一化)
        actual_rotation_axis_np = initial_user_up_np 
        
        # 3. 需要被旋转的向量是：从旋转中心指向初始相机位置的向量
        vec_to_rotate_np = initial_user_origin_np - rotation_center_np
        
        # 4. 为了保持相机姿态，我们需要一个稳定的、与初始视线正交的up向量进行旋转
        initial_view_dir = normalize(initial_user_target_np - initial_user_origin_np)
        initial_camera_right = normalize(np.cross(initial_view_dir, initial_user_up_np))
        true_initial_camera_up_for_rotation = normalize(np.cross(initial_camera_right, initial_view_dir))
    
    # --- 循环生成帧 --- 
    frame_iterable = range(args.frames)
    if TQDM_AVAILABLE:
        frame_iterable = tqdm(range(args.frames), desc="渲染帧", unit="frame", ncols=100, 
                              bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}{postfix}]')

    for i in frame_iterable:
        current_cam_origin_str, current_cam_target_str, current_cam_up_str = "", "", ""
        display_angle_deg_for_print = 0.0

        base_angle_deg_for_cycle = (i / args.frames) * 360.0
        effective_angle_deg = base_angle_deg_for_cycle # 默认，对于 initial_up，没有offset和elevation
        
        if args.rotation_axis == 'initial_up':
            if args.clockwise:
                 effective_angle_deg = -base_angle_deg_for_cycle # Scipy Rotation 接受负角度
            else:
                 effective_angle_deg = base_angle_deg_for_cycle
            display_angle_deg_for_print = effective_angle_deg % 360.0

            rot = Rotation.from_rotvec(math.radians(effective_angle_deg) * actual_rotation_axis_np)
            
            rotated_offset = rot.apply(vec_to_rotate_np)
            current_origin_np = rotation_center_np + rotated_offset
            
            # 相机渲染时，点云会被移到(0,0,0)，target也应该是(0,0,0)
            # 所以我们需要调整 current_origin_np，使得 current_origin_np -> (0,0,0) 这个向量
            # 等于 current_origin_np (上面计算的) -> rotation_center_np (用户指定的target)
            # 即 view_vector = rotation_center_np - current_origin_np
            # final_cam_origin_for_render = np.array([0,0,0]) - view_vector
            view_vector_to_user_target = rotation_center_np - current_origin_np
            final_cam_origin_for_render = np.array([0.0,0.0,0.0]) - view_vector_to_user_target

            final_cam_target_for_render = np.array([0.0,0.0,0.0])
            final_cam_up_for_render = rot.apply(true_initial_camera_up_for_rotation)

            current_cam_origin_str = f"{final_cam_origin_for_render[0]},{final_cam_origin_for_render[1]},{final_cam_origin_for_render[2]}"
            current_cam_target_str = f"{final_cam_target_for_render[0]},{final_cam_target_for_render[1]},{final_cam_target_for_render[2]}"
            current_cam_up_str = f"{final_cam_up_for_render[0]},{final_cam_up_for_render[1]},{final_cam_up_for_render[2]}"
        
        else: # 世界轴旋转 (x, y, z)
            if args.clockwise:
                effective_angle_deg = args.start_angle_offset_deg - base_angle_deg_for_cycle
            else:
                effective_angle_deg = args.start_angle_offset_deg + base_angle_deg_for_cycle
            display_angle_deg_for_print = effective_angle_deg % 360.0
            angle_rad = math.radians(effective_angle_deg)
            
            elevation_rad = math.radians(args.camera_elevation_deg)
            dist_on_rotation_plane = args.camera_distance * math.cos(elevation_rad)
            cam_offset_along_elevation_axis = args.camera_distance * math.sin(elevation_rad)
            x_rot_plane = dist_on_rotation_plane * math.cos(angle_rad)
            y_rot_plane = dist_on_rotation_plane * math.sin(angle_rad)
            
            cam_origin_np_world, cam_up_np_world = np.array([0.0,0.0,0.0]), np.array([0.0,0.0,1.0])
            cam_target_np_world = np.array([0.0,0.0,0.0]) # 固定目标

            if args.rotation_axis == 'z':
                cam_origin_np_world = np.array([x_rot_plane, y_rot_plane, cam_offset_along_elevation_axis])
                cam_up_np_world = np.array([0, 0, 1.0])
                if abs(args.camera_elevation_deg) > 89.5:
                     cam_up_np_world = np.array([-math.cos(angle_rad), -math.sin(angle_rad), 0.0])
            elif args.rotation_axis == 'y':
                cam_origin_np_world = np.array([x_rot_plane, cam_offset_along_elevation_axis, y_rot_plane])
                cam_up_np_world = np.array([0, 1.0, 0])
                if abs(args.camera_elevation_deg) > 89.5: # Simplified from previous complex logic
                    cam_up_np_world = np.array([math.cos(angle_rad),0,-math.sin(angle_rad)]) # roughly points away from Z axis on XZ plane
            elif args.rotation_axis == 'x':
                cam_origin_np_world = np.array([cam_offset_along_elevation_axis, y_rot_plane, x_rot_plane])
                cam_up_np_world = np.array([1.0, 0, 0])
                if abs(args.camera_elevation_deg) > 89.5:
                    cam_up_np_world = np.array([0,math.cos(angle_rad),-math.sin(angle_rad)]) # roughly points away from Y axis on YZ plane
            
            current_cam_origin_str = f"{cam_origin_np_world[0]},{cam_origin_np_world[1]},{cam_origin_np_world[2]}"
            current_cam_target_str = f"{cam_target_np_world[0]},{cam_target_np_world[1]},{cam_target_np_world[2]}"
            current_cam_up_str = f"{cam_up_np_world[0]},{cam_up_np_world[1]},{cam_up_np_world[2]}"

        camera_params_for_render = f"{current_cam_origin_str} {current_cam_target_str} {current_cam_up_str}"
        output_frame_prefix = f"frame_{i:03d}"
        render_cmd = [
            sys.executable, args.render_script_path, args.input_file,
            "--output_dir", args.temp_dir_frames, "--output_prefix", output_frame_prefix,
            "--output_format", "png", 
            "--camera_params", camera_params_for_render, "--fov", str(args.fov),
            "--resolution", str(args.resolution[0]), str(args.resolution[1]),
            "--samples", str(args.samples), "--point_radius", str(args.point_radius),
            "--color_mode", args.color_mode, "--color_map", args.color_map, "--cleanup"
        ]
        
        # 如果启用了贴附平面，添加相关参数（会自动禁用原始地面平面）
        if args.attach_ground:
            render_cmd.append("--attach_ground")
            render_cmd.extend(["--attached_ground_offset", str(args.attached_ground_offset)])
            render_cmd.extend(["--attached_ground_size", str(args.attached_ground_size)])
        else:
            # 如果没有启用贴附平面，则明确指定是否需要原始地面平面
            render_cmd.append("--no_ground")  # 在转盘动画中默认禁用原始地面平面
        
        # 添加环境光强度参数
        render_cmd.extend(["--env_light_intensity", str(args.env_light_intensity)])
        
        # 添加背景颜色参数
        render_cmd.extend(["--background_color", str(args.background_color[0]), str(args.background_color[1]), str(args.background_color[2])])
        
        render_cmd.extend(["--num_points", str(args.num_render_points)])

        if args.fixed_color and args.color_mode == "fixed":
            render_cmd.extend(["--fixed_color", str(args.fixed_color[0]), str(args.fixed_color[1]), str(args.fixed_color[2])])
        if args.color_mode == "height":
             render_cmd.extend(["--color_axis", str(args.color_axis)])

        if args.mitsuba_path: render_cmd.extend(["--mitsuba_path", args.mitsuba_path])
        
        if TQDM_AVAILABLE:
            frame_iterable.set_postfix_str(f"角度: {display_angle_deg_for_print:.1f}°")
        else:
            print(f"正在渲染第 {i+1}/{args.frames} 帧 (角度: {display_angle_deg_for_print:.1f} 度)...", flush=True)

        try:
            result = subprocess.run(render_cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
            # print(result.stdout) # 打印 render_point_cloud.py 的输出
            
            expected_frame_file = os.path.join(args.temp_dir_frames, f"{output_frame_prefix}.png")
            if os.path.exists(expected_frame_file):
                 frame_files.append(expected_frame_file)
            else:
                message = f"警告: 未找到预期的帧文件: {expected_frame_file}"
                if TQDM_AVAILABLE: frame_iterable.write(message)
                else: print(message)
        except subprocess.CalledProcessError as e:
            error_message = f"渲染第 {i+1} 帧时发生错误: {e.returncode}"
            if TQDM_AVAILABLE: frame_iterable.write(error_message)
            else: print(error_message)
            if e.stdout: print(f"  Stdout:\n{e.stdout}")
            if e.stderr: print(f"  Stderr:\n{e.stderr}")
            # return 1 # 出现第一个错误时停止

    if TQDM_AVAILABLE and isinstance(frame_iterable, tqdm):
        frame_iterable.close()

    if not frame_files:
        print("未成功渲染任何帧。无法创建GIF。")
        if os.path.exists(args.temp_dir_frames) and not args.keep_frames:
            print(f"正在清理临时目录: {args.temp_dir_frames}")
            shutil.rmtree(args.temp_dir_frames)
        return 1
    
    if len(frame_files) < args.frames:
        print(f"警告: 预期渲染 {args.frames} 帧, 但只找到了 {len(frame_files)} 帧。")

    frame_files.sort() # 确保帧顺序正确

    print(f"正在从 {len(frame_files)} 帧创建GIF: {args.output_gif} ...")
    try:
        images = [iio.imread(f) for f in frame_files]
        iio.mimsave(args.output_gif, images, duration=args.duration * 1000, loop=0) # duration in ms for imageio
        print("GIF创建成功。")
    except Exception as e:
        print(f"创建GIF时发生错误: {e}")
        return 1

    if not args.keep_frames:
        print(f"正在清理临时帧目录: {args.temp_dir_frames}")
        shutil.rmtree(args.temp_dir_frames)
    
    print(f"输出GIF已保存到: {os.path.abspath(args.output_gif)}")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 