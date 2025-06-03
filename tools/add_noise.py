#!/usr/bin/env python
"""
Mitsuba2 点云渲染器 - 点云添加噪声工具

为点云添加高斯噪声。
"""

import os
import sys
import argparse
import numpy as np
import open3d as o3d

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mitsuba_pcr.utils.io import load_point_cloud, save_points_to_ply

def add_gaussian_noise(points, noise_std=0.01):
    """
    为点云添加高斯噪声
    
    参数:
        points (numpy.ndarray): 输入点云，形状为(N, 3)
        noise_std (float): 高斯噪声标准差
    
    返回:
        numpy.ndarray: 添加噪声后的点云，形状为(N, 3)
    """
    if points is None or points.shape[0] == 0:
        return points
    
    # 生成高斯噪声
    noise = np.random.normal(loc=0.0, scale=noise_std, size=points.shape)
    
    # 添加噪声
    noisy_points = points + noise
    
    return noisy_points

def main():
    parser = argparse.ArgumentParser(description="为点云添加高斯噪声")
    parser.add_argument("input_file", help="输入点云文件路径 (.ply, .npy, .npz)")
    parser.add_argument("--noise_std", type=float, default=0.01, help="高斯噪声标准差 (默认: 0.01)")
    parser.add_argument("--output_file", help="输出文件路径，默认为在输入文件名后添加'_noisy_X'，其中X是噪声标准差")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    
    args = parser.parse_args()
    
    # 设置随机种子
    np.random.seed(args.seed)
    
    # 加载点云
    points, colors = load_point_cloud(args.input_file)
    if points is None:
        return 1
    
    print(f"原始点数: {points.shape[0]}")
    
    # 添加噪声
    noisy_points = add_gaussian_noise(points, args.noise_std)
    
    # 准备输出文件路径
    if args.output_file:
        output_file = args.output_file
    else:
        base, ext = os.path.splitext(args.input_file)
        noise_str = f"{args.noise_std:.3f}".rstrip('0').rstrip('.')
        output_file = f"{base}_noisy_{noise_str}{ext}"
    
    # 保存结果
    if output_file.lower().endswith('.ply'):
        success = save_points_to_ply(noisy_points, colors, output_file)
    else:
        try:
            if colors is not None and colors.shape[0] == noisy_points.shape[0]:
                # 如果有颜色，将点和颜色一起保存
                data = np.column_stack((noisy_points, colors))
            else:
                data = noisy_points
            np.save(output_file, data)
            print(f"已保存带噪点云: {output_file}")
            success = True
        except Exception as e:
            print(f"保存点云到 '{output_file}' 时发生错误: {e}")
            success = False
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 