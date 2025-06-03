"""
颜色处理模块

提供点云颜色的处理、转换和生成功能。
"""

import numpy as np

def srgb_to_linear(srgb_color):
    """
    将sRGB颜色值转换为线性颜色值
    
    参数:
        srgb_color (float or numpy.ndarray): sRGB颜色值，范围[0, 1]
    
    返回:
        float or numpy.ndarray: 线性颜色值
    """
    if isinstance(srgb_color, np.ndarray):
        return np.where(
            srgb_color <= 0.04045,
            srgb_color / 12.92,
            ((srgb_color + 0.055) / 1.055) ** 2.4
        )
    else:
        if srgb_color <= 0.04045:
            return srgb_color / 12.92
        else:
            return ((srgb_color + 0.055) / 1.055) ** 2.4

def linear_to_srgb(linear_color):
    """
    将线性颜色值转换为sRGB颜色值
    
    参数:
        linear_color (float or numpy.ndarray): 线性颜色值
    
    返回:
        float or numpy.ndarray: sRGB颜色值，范围[0, 1]
    """
    if isinstance(linear_color, np.ndarray):
        return np.where(
            linear_color <= 0.0031308,
            linear_color * 12.92,
            1.055 * (linear_color ** (1/2.4)) - 0.055
        )
    else:
        if linear_color <= 0.0031308:
            return linear_color * 12.92
        else:
            return 1.055 * (linear_color ** (1/2.4)) - 0.055

def position_based_colormap(points):
    """
    基于点的位置生成颜色
    
    参数:
        points (numpy.ndarray): 点坐标，形状为(N, 3)
    
    返回:
        numpy.ndarray: 颜色值，形状为(N, 3)，范围[0, 1]
    """
    if points is None or points.shape[0] == 0:
        return None
    
    # 将坐标归一化到[0, 1]范围
    normalized_points = points.copy()
    normalized_points -= np.min(normalized_points, axis=0)
    max_vals = np.max(normalized_points, axis=0)
    max_vals[max_vals == 0] = 1  # 避免除以零
    normalized_points /= max_vals
    
    # 使用归一化的坐标作为颜色
    colors = normalized_points.copy()
    
    # 确保颜色在有效范围内
    colors = np.clip(colors, 0.001, 1.0)
    
    # 归一化颜色向量长度
    norms = np.sqrt(np.sum(colors ** 2, axis=1, keepdims=True))
    norms[norms == 0] = 1  # 避免除以零
    colors /= norms
    
    return colors

def height_based_colormap(points, axis=2, cmap='viridis'):
    """
    基于点的高度（或指定轴的值）生成颜色
    
    参数:
        points (numpy.ndarray): 点坐标，形状为(N, 3)
        axis (int): 用于确定"高度"的坐标轴，0=X, 1=Y, 2=Z
        cmap (str): 颜色映射名称，支持'viridis', 'jet', 'rainbow', 'turbo'
    
    返回:
        numpy.ndarray: 颜色值，形状为(N, 3)，范围[0, 1]
    """
    if points is None or points.shape[0] == 0:
        return None
    
    # 提取指定轴的值
    values = points[:, axis]
    
    # 归一化到[0, 1]范围
    v_min, v_max = np.min(values), np.max(values)
    if v_min == v_max:
        normalized = np.zeros_like(values)
    else:
        normalized = (values - v_min) / (v_max - v_min)
    
    # 应用颜色映射
    if cmap == 'jet':
        return jet_colormap(normalized)
    elif cmap == 'rainbow':
        return rainbow_colormap(normalized)
    elif cmap == 'turbo':
        return turbo_colormap(normalized)
    else:  # 默认使用viridis
        return viridis_colormap(normalized)

def custom_colormap(points, color_function):
    """
    使用自定义颜色函数为点云生成颜色
    
    参数:
        points (numpy.ndarray): 点坐标，形状为(N, 3)
        color_function (callable): 自定义颜色函数，接收点坐标返回颜色值
    
    返回:
        numpy.ndarray: 颜色值，形状为(N, 3)，范围[0, 1]
    """
    if points is None or points.shape[0] == 0:
        return None
    
    try:
        colors = color_function(points)
        if colors.shape != points.shape:
            print(f"警告: 自定义颜色函数返回的形状 {colors.shape} 与点云形状 {points.shape} 不匹配。")
            return None
        return np.clip(colors, 0, 1)  # 确保颜色在[0, 1]范围内
    except Exception as e:
        print(f"应用自定义颜色函数时发生错误: {e}")
        return None

def apply_colormap(points, mode="position", **kwargs):
    """
    为点云应用颜色映射
    
    参数:
        points (numpy.ndarray): 点坐标，形状为(N, 3)
        mode (str): 颜色映射模式
            - "position": 基于位置的颜色映射
            - "height": 基于高度的颜色映射
            - "custom": 自定义颜色映射函数
        **kwargs: 额外参数，根据mode不同而不同
            - 对于"height": axis, cmap
            - 对于"custom": color_function
    
    返回:
        numpy.ndarray: 颜色值，形状为(N, 3)，范围[0, 1]
    """
    if mode == "position":
        return position_based_colormap(points)
    elif mode == "height":
        axis = kwargs.get("axis", 2)
        cmap = kwargs.get("cmap", "viridis")
        return height_based_colormap(points, axis, cmap)
    elif mode == "custom" and "color_function" in kwargs:
        return custom_colormap(points, kwargs["color_function"])
    elif mode == "fixed" and "color" in kwargs:
        color = np.array(kwargs["color"])
        return np.tile(color, (points.shape[0], 1))
    else:
        print(f"警告: 未知的颜色映射模式 '{mode}'，将使用基于位置的颜色映射。")
        return position_based_colormap(points)

# 以下是几种常用的颜色映射函数的简化实现

def viridis_colormap(values):
    """简化版的viridis颜色映射"""
    # 这是一个极简化的viridis映射，实际应用中可以使用matplotlib的实现
    colors = np.zeros((len(values), 3))
    for i, t in enumerate(values):
        colors[i, 0] = 0.267004 + t * 0.405133
        colors[i, 1] = 0.004874 + t * 0.838762
        colors[i, 2] = 0.329415 + t * 0.276025
    return np.clip(colors, 0, 1)

def jet_colormap(values):
    """简化版的jet颜色映射"""
    colors = np.zeros((len(values), 3))
    for i, t in enumerate(values):
        if t < 0.125:
            colors[i, 0] = 0
            colors[i, 1] = 0
            colors[i, 2] = 0.5 + 4 * t
        elif t < 0.375:
            colors[i, 0] = 0
            colors[i, 1] = 4 * (t - 0.125)
            colors[i, 2] = 1
        elif t < 0.625:
            colors[i, 0] = 4 * (t - 0.375)
            colors[i, 1] = 1
            colors[i, 2] = 1 - 4 * (t - 0.375)
        elif t < 0.875:
            colors[i, 0] = 1
            colors[i, 1] = 1 - 4 * (t - 0.625)
            colors[i, 2] = 0
        else:
            colors[i, 0] = 1 - 4 * (t - 0.875)
            colors[i, 1] = 0
            colors[i, 2] = 0
    return colors

def rainbow_colormap(values):
    """简化版的rainbow颜色映射"""
    colors = np.zeros((len(values), 3))
    for i, t in enumerate(values):
        colors[i, 0] = np.abs(np.sin(2 * np.pi * t))
        colors[i, 1] = np.sin(2 * np.pi * (t + 1/3)) * 0.5 + 0.5
        colors[i, 2] = np.sin(2 * np.pi * (t + 2/3)) * 0.5 + 0.5
    return np.clip(colors, 0, 1)

def turbo_colormap(values):
    """简化版的turbo颜色映射"""
    colors = np.zeros((len(values), 3))
    for i, t in enumerate(values):
        colors[i, 0] = 0.13572138 + 4.61539260 * t - 42.66032258 * t**2 + 132.13839591 * t**3 - 151.59036175 * t**4 + 62.35964731 * t**5
        colors[i, 1] = 0.09140261 + 2.19418839 * t + 4.84296658 * t**2 - 14.18503333 * t**3 + 4.27729857 * t**4 + 2.82956604 * t**5
        colors[i, 2] = 0.10667330 + 12.64194608 * t - 60.58204836 * t**2 + 110.36276771 * t**3 - 89.90310912 * t**4 + 27.34824973 * t**5
    return np.clip(colors, 0, 1)