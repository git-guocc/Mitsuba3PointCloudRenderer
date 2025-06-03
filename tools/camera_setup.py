#!/usr/bin/env python
"""
Mitsuba2 点云渲染器 - 相机设置工具

交互式工具，用于设置Mitsuba2渲染的相机参数。
"""

import os
import sys
import argparse
import numpy as np
import open3d as o3d

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mitsuba_pcr.utils.io import load_point_cloud
from mitsuba_pcr.utils.transform import standardize_bbox, transform_camera_params

def adjust_camera_distance(origin, target, distance_multiplier):
    """调整相机距离，保持视角方向不变"""
    direction_target_to_origin = origin - target
    current_dist = np.linalg.norm(direction_target_to_origin)
    if current_dist < 1e-6: 
        print("警告：相机原点与目标点重合，距离调整可能无效。")
        return origin 
    
    direction_unit = direction_target_to_origin / current_dist
    new_dist = current_dist * distance_multiplier
    new_origin = target + direction_unit * new_dist
    return new_origin

def parse_camera_params(param_string):
    """解析相机参数字符串"""
    try:
        # 分割字符串并转换为浮点数
        values = [float(x) for x in param_string.split()]
        if len(values) != 7:
            print("错误：需要7个数值 (front_x front_y front_z lookat_x lookat_y lookat_z up_x)")
            return None
            
        return {
            'front': values[0:3],
            'lookat': values[3:6],
            'up': [values[6], 0, 0]  # 只使用第一个值作为up的x分量
        }
    except ValueError:
        print("错误：输入格式不正确，请确保所有值都是数字")
        return None

def main():
    parser = argparse.ArgumentParser(description="交互式相机设置工具，用于Mitsuba2点云渲染")
    parser.add_argument("input_file", help="输入点云文件路径 (.ply, .npy, .npz)")
    parser.add_argument("--initial_params", help="初始相机参数 (7个数字，用空格分隔)")
    
    args = parser.parse_args()
    
    # 加载点云
    points, colors = load_point_cloud(args.input_file)
    if points is None:
        return 1
    
    # 标准化点云
    points_normalized = standardize_bbox(points)
    
    # 解析初始相机参数
    initial_camera_params = None
    if args.initial_params:
        initial_camera_params = parse_camera_params(args.initial_params)
        if initial_camera_params is None:
            print("将使用默认视角")
    
    # 创建Open3D点云对象
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points_normalized)
    if colors is not None:
        pcd.colors = o3d.utility.Vector3dVector(colors)
    else:
        pcd.paint_uniform_color([0.7, 0.7, 0.7])
    
    # 添加坐标系
    coordinate_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.3, origin=[0, 0, 0])
    
    # 打开可视化窗口
    print("\n正在打开Open3D可视化窗口...")
    print("请调整您期望的渲染视角，然后按 'Q' 键关闭窗口。")
    vis = o3d.visualization.VisualizerWithEditing()
    vis.create_window(window_name="调整点云视角", width=1024, height=768)
    vis.add_geometry(pcd)
    vis.add_geometry(coordinate_frame)
    
    view_control = vis.get_view_control()
    
    # 如果提供了相机参数，则设置初始视角
    if initial_camera_params:
        view_control.set_front(initial_camera_params['front'])
        view_control.set_lookat(initial_camera_params['lookat'])
        view_control.set_up(initial_camera_params['up'])
        view_control.set_zoom(0.7)
    
    vis.run()
    pinhole_params = view_control.convert_to_pinhole_camera_parameters()
    open3d_fov_vertical_deg = view_control.get_field_of_view()
    vis.destroy_window()
    
    # 获取相机参数
    extrinsic = pinhole_params.extrinsic  # World-to-Camera
    extrinsic_inv = np.linalg.inv(extrinsic)  # Camera-to-World
    o3d_camera_origin_world = extrinsic_inv[:3, 3]
    o3d_camera_up_world = extrinsic_inv[:3, 1]
    
    # 计算点云中心
    cloud_center = np.mean(points_normalized, axis=0)
    
    # 初始相机参数
    mitsuba_target = cloud_center
    mitsuba_origin = o3d_camera_origin_world
    
    # 可选的相机距离调整
    answer = input("\n是否需要调整相机与点云中心的距离？(y/n，默认为n): ").lower()
    if answer == 'y':
        try:
            multiplier = float(input("请输入距离倍数（>1 表示拉远，<1 表示拉近，例如 1.5 表示拉远50%）: "))
            mitsuba_origin = adjust_camera_distance(o3d_camera_origin_world, mitsuba_target, multiplier)
            print(f"相机距离已按因子 {multiplier} 调整。")
        except ValueError:
            print("输入无效，使用原始相机距离。")
    
    # 转换为Mitsuba相机参数
    mitsuba_origin, mitsuba_target, mitsuba_up = transform_camera_params(
        mitsuba_origin, mitsuba_target, o3d_camera_up_world
    )
    
    # 计算Mitsuba FOV
    mitsuba_film_width = 3840
    mitsuba_film_height = 2160
    aspect_ratio = mitsuba_film_width / mitsuba_film_height
    mitsuba_fov_horizontal_deg = np.rad2deg(2 * np.arctan(aspect_ratio * np.tan(np.deg2rad(open3d_fov_vertical_deg) / 2.0)))
    
    # 输出结果
    print("\n--- Mitsuba相机参数 ---")
    print(f'origin="{mitsuba_origin[0]},{mitsuba_origin[1]},{mitsuba_origin[2]}"')
    print(f'target="{mitsuba_target[0]},{mitsuba_target[1]},{mitsuba_target[2]}"')
    print(f'up="{mitsuba_up[0]},{mitsuba_up[1]},{mitsuba_up[2]}"')
    
    print("\n--- 用于命令行参数 ---")
    camera_param_str = f"{mitsuba_origin[0]},{mitsuba_origin[1]},{mitsuba_origin[2]} {mitsuba_target[0]},{mitsuba_target[1]},{mitsuba_target[2]} {mitsuba_up[0]},{mitsuba_up[1]},{mitsuba_up[2]}"
    print(f'--camera_params "{camera_param_str}" --fov {mitsuba_fov_horizontal_deg:.2f}')
    
    print("\n--- 可直接复制到XML ---")
    print(f'<lookat origin="{mitsuba_origin[0]},{mitsuba_origin[1]},{mitsuba_origin[2]}" target="{mitsuba_target[0]},{mitsuba_target[1]},{mitsuba_target[2]}" up="{mitsuba_up[0]},{mitsuba_up[1]},{mitsuba_up[2]}"/>')
    print(f'<float name="fov" value="{mitsuba_fov_horizontal_deg:.2f}"/>')
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 