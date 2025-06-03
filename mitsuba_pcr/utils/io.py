"""
文件IO操作模块

提供点云文件的读取和结果文件的保存功能。
支持的点云格式：.ply, .npy, .npz, .xyz
支持的输出格式：.exr, .png, .jpg
"""

import numpy as np
import os
import OpenEXR
import Imath
from PIL import Image
import open3d as o3d

def load_point_cloud(filepath):
    """
    加载点云文件，支持.ply, .npy, .npz格式
    
    参数:
        filepath (str): 点云文件路径
    
    返回:
        tuple: (points, colors), 其中:
            - points: numpy数组，形状为(N, 3)，表示点坐标
            - colors: numpy数组，形状为(N, 3)，表示点颜色，如果没有颜色则为None
    """
    filename, file_extension = os.path.splitext(filepath)
    file_extension = file_extension.lower()
    
    points = None
    colors = None
    
    try:
        if file_extension == '.ply':
            pcd = o3d.io.read_point_cloud(filepath)
            if not pcd.has_points():
                print(f"错误: PLY 文件 {filepath} 不包含点。")
                return None, None
            points = np.asarray(pcd.points)
            if pcd.has_colors():
                colors = np.asarray(pcd.colors)
                print(f"成功从 PLY 文件加载 {points.shape[0]} 个点和对应的颜色。")
            else:
                print(f"成功从 PLY 文件加载 {points.shape[0]} 个点（无颜色信息）。")
        
        elif file_extension == '.npy':
            data = np.load(filepath)
            if data.ndim == 2:
                if data.shape[1] >= 3:
                    points = data[:, :3]
                    if data.shape[1] >= 6:  # 假设后三列是颜色
                        colors = data[:, 3:6]
                        print(f"成功从 NPY 文件加载 {points.shape[0]} 个点和对应的颜色。")
                    else:
                        print(f"成功从 NPY 文件加载 {points.shape[0]} 个点（无颜色信息）。")
                else:
                    print(f"错误: NPY 文件 {filepath} 中的数据维度不正确，每个点至少需要3个坐标。")
                    return None, None
            elif data.ndim == 3:
                # 多帧点云数据，取第一帧
                print(f"检测到多帧点云数据，将使用第一帧。总帧数: {data.shape[0]}")
                points = data[0, :, :3]
                print(f"成功从 NPY 文件加载 {points.shape[0]} 个点（无颜色信息）。")
            else:
                print(f"错误: NPY 文件 {filepath} 的维度不支持: {data.shape}")
                return None, None
        
        elif file_extension == '.npz':
            data = np.load(filepath)
            if 'points' in data:
                points = data['points']
                if points.ndim == 3:
                    # 多帧点云数据，取第一帧
                    print(f"检测到多帧点云数据，将使用第一帧。总帧数: {points.shape[0]}")
                    points = points[0]
                if 'colors' in data:
                    colors = data['colors']
                    if colors.ndim == 3:
                        # 多帧颜色数据，取第一帧
                        colors = colors[0]
                    print(f"成功从 NPZ 文件加载 {points.shape[0]} 个点和对应的颜色。")
                else:
                    print(f"成功从 NPZ 文件加载 {points.shape[0]} 个点（无颜色信息）。")
            elif 'pred' in data:
                points = data['pred']
                if points.ndim == 3:
                    # 多帧点云数据，取第一帧
                    print(f"检测到多帧点云数据，将使用第一帧。总帧数: {points.shape[0]}")
                    points = points[0]
                print(f"成功从 NPZ 文件加载 {points.shape[0]} 个点（无颜色信息）。")
            else:
                print(f"错误: NPZ 文件 {filepath} 不包含 'points' 或 'pred' 键。")
                return None, None
        elif file_extension == '.xyz':
            # 读取xyz格式，支持 x y z 或 x y z r g b
            data = np.loadtxt(filepath)
            if data.ndim == 1:
                data = data.reshape(1, -1)
            if data.shape[1] >= 3:
                points = data[:, :3]
                if data.shape[1] >= 6:
                    # 判断颜色是否为0-255区间，若是则归一化
                    color_data = data[:, 3:6]
                    if color_data.max() > 1:
                        colors = color_data / 255.0
                    else:
                        colors = color_data
                    print(f"成功从 XYZ 文件加载 {points.shape[0]} 个点和对应的颜色。")
                else:
                    print(f"成功从 XYZ 文件加载 {points.shape[0]} 个点（无颜色信息）。")
            else:
                print(f"错误: XYZ 文件 {filepath} 中的数据维度不正确，每个点至少需要3个坐标。")
                return None, None
        else:
            print(f"错误: 不支持的文件格式 '{file_extension}'。支持的格式: .ply, .npy, .npz, .xyz")
            return None, None
    except Exception as e:
        print(f"加载文件 {filepath} 时发生错误: {e}")
        return None, None
    
    return points, colors

def convert_exr_to_image(exr_file, output_file, flip_horizontal=False):
    """
    将EXR文件转换为常规图像格式(PNG/JPG)
    
    参数:
        exr_file (str): 输入EXR文件路径
        output_file (str): 输出图像文件路径
        flip_horizontal (bool): 是否水平翻转图像
    
    返回:
        bool: 转换是否成功
    """
    try:
        # 打开EXR文件
        exr = OpenEXR.InputFile(exr_file)
        pixel_type = Imath.PixelType(Imath.PixelType.FLOAT)
        data_window = exr.header()['dataWindow']
        size = (data_window.max.x - data_window.min.x + 1, data_window.max.y - data_window.min.y + 1)

        # 读取RGB通道
        rgb = [np.frombuffer(exr.channel(c, pixel_type), dtype=np.float32) for c in 'RGB']
        
        # sRGB EOTF (gamma校正)
        for i in range(3):
            rgb[i] = np.where(rgb[i] <= 0.0031308,
                              (rgb[i] * 12.92) * 255.0,
                              (1.055 * (rgb[i] ** (1.0 / 2.4)) - 0.055) * 255.0)

        # 转换为PIL图像
        rgb8 = [Image.frombytes("F", size, c.tobytes()).convert("L") for c in rgb]
        merged_image = Image.merge("RGB", rgb8)
        
        # 如果需要，水平翻转图像
        if flip_horizontal:
            merged_image = merged_image.transpose(Image.FLIP_LEFT_RIGHT)
        
        # 确定输出格式
        output_format = os.path.splitext(output_file)[1].upper()[1:]
        if not output_format or output_format not in ['PNG', 'JPG', 'JPEG']:
            output_format = 'PNG'
            if not output_file.lower().endswith(('.png', '.jpg', '.jpeg')):
                output_file += '.png'
        
        # 保存图像
        if output_format == 'JPG' or output_format == 'JPEG':
            merged_image.save(output_file, 'JPEG', quality=95)
        else:
            merged_image.save(output_file, 'PNG')
            
        print(f"已将 EXR 转换为 {output_format}: {output_file}")
        return True
    except Exception as e:
        print(f"转换 EXR 到图像时发生错误: {e}")
        return False

def save_points_to_ply(points, colors=None, ply_filepath=None):
    """
    将点云数据保存为PLY文件
    
    参数:
        points (numpy.ndarray): 点坐标数组，形状为(N, 3)
        colors (numpy.ndarray, optional): 点颜色数组，形状为(N, 3)，范围0-1
        ply_filepath (str): 输出PLY文件路径
    
    返回:
        bool: 保存是否成功
    """
    if points is None or points.shape[0] == 0:
        print("错误: 点云数据为空，无法保存PLY文件。")
        return False
    
    try:
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        
        if colors is not None:
            if colors.shape[0] == points.shape[0]:
                pcd.colors = o3d.utility.Vector3dVector(colors)
            else:
                print(f"警告: 颜色数量 ({colors.shape[0]}) 与点数量 ({points.shape[0]}) 不匹配，将不使用颜色。")
        
        success = o3d.io.write_point_cloud(ply_filepath, pcd)
        if success:
            print(f"成功保存点云到: {ply_filepath}")
        else:
            print(f"保存点云到 {ply_filepath} 失败。")
        return success
    except Exception as e:
        print(f"保存PLY文件 '{ply_filepath}' 时发生错误: {e}")
        return False 