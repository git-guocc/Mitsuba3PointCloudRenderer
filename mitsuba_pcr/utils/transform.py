"""
坐标变换模块

提供点云坐标的标准化、变换和处理功能。
"""

import numpy as np

def standardize_bbox(points, points_per_object=None):
    """
    将点云标准化到[-0.5, 0.5]范围内，并可选地对点进行采样
    
    参数:
        points (numpy.ndarray): 输入点云，形状为(N, 3)
        points_per_object (int, optional): 采样的点数，如果为None或小于等于0，则使用所有点
    
    返回:
        numpy.ndarray: 标准化后的点云，形状为(min(N, points_per_object), 3)
    """
    if points is None or points.shape[0] == 0:
        print("错误：点云数据为空。")
        return points
    
    # 采样点云（如果需要）
    points_to_process = points
    if points_per_object is not None and points_per_object > 0:
        if points.shape[0] > points_per_object:
            print(f"将从 {points.shape[0]} 个原始点中采样 {points_per_object} 个点。")
            indices = np.random.choice(points.shape[0], points_per_object, replace=False)
            points_to_process = points[indices]
        else:
            print(f"原始点云点数 ({points.shape[0]}) 少于或等于目标点数 ({points_per_object})。将使用所有点。")
    
    # 计算边界框和中心
    mins = np.amin(points_to_process, axis=0)
    maxs = np.amax(points_to_process, axis=0)
    center = (mins + maxs) / 2.
    scale = np.amax(maxs - mins)
    
    # 处理scale接近零的情况
    if abs(scale) < 1e-9:
        print("警告: 点云缩放比例接近零，将使用默认值1.0。")
        scale = 1.0
        
    print(f"标准化 Center: {center}, Scale: {scale} (基于 {points_to_process.shape[0]} 个点)")
    
    # 标准化到[-0.5, 0.5]范围
    normalized_points = ((points_to_process - center) / scale).astype(np.float32)
    return normalized_points

def transform_for_mitsuba(points):
    """
    将标准化后的点云转换为Mitsuba渲染所需的坐标系
    
    参数:
        points (numpy.ndarray): 输入点云，形状为(N, 3)，已标准化到[-0.5, 0.5]
    
    返回:
        numpy.ndarray: 转换后的点云，形状为(N, 3)
    """
    if points is None or points.shape[0] == 0:
        return points
    
    # 坐标轴变换: (x,y,z) -> (-z,x,y)
    transformed = points[:, [2, 0, 1]].copy()
    transformed[:, 0] *= -1
    
    # 添加小偏移，避免点与地面完全重合
    transformed[:, 2] += 0.0125
    
    return transformed

def transform_camera_params(o3d_origin, o3d_target, o3d_up):
    """
    将Open3D相机参数转换为Mitsuba相机参数
    
    参数:
        o3d_origin (numpy.ndarray): Open3D相机原点，形状为(3,)
        o3d_target (numpy.ndarray): Open3D相机目标点，形状为(3,)
        o3d_up (numpy.ndarray): Open3D相机上方向，形状为(3,)
    
    返回:
        tuple: (mitsuba_origin, mitsuba_target, mitsuba_up)，每个元素都是形状为(3,)的numpy数组
    """
    # Origin: (x,y,z) -> (-z,x,y)
    mitsuba_origin = np.array([
        -o3d_origin[2],
        o3d_origin[0],
        o3d_origin[1]
    ])
    
    # Target: (x,y,z) -> (-z,x,y)
    mitsuba_target = np.array([
        -o3d_target[2],
        o3d_target[0],
        o3d_target[1]  # 原始 Y 轴
    ])
    mitsuba_target[2] += 0.0125  # 对变换后的 Z 轴 (即原始的 Y 轴) 添加与点云相同的偏移
    
    # Up: (x,y,z) -> (-z,x,y)
    # To match camera.py logic, negate o3d_up before transformation
    neg_o3d_up = -o3d_up
    mitsuba_up = np.array([
        -neg_o3d_up[2],
        neg_o3d_up[0],
        neg_o3d_up[1]
    ])
    
    return mitsuba_origin, mitsuba_target, mitsuba_up 