#!/usr/bin/env python
"""
Mitsuba2 点云渲染器 - 网格采样工具

从3D网格（OBJ或STL）表面采样点云。
"""

import os
import sys
import argparse
import numpy as np
from stl import mesh as stl_mesh

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mitsuba_pcr.utils.io import save_points_to_ply

def parse_obj_to_mesh_data(obj_filepath):
    """
    从OBJ文件中解析顶点和面数据
    
    参数:
        obj_filepath (str): OBJ文件路径
    
    返回:
        tuple: (vertices, faces)，其中:
            - vertices: numpy数组，形状为(V, 3)，表示顶点坐标
            - faces: numpy数组，形状为(F, 3)，表示三角面片顶点索引
    """
    vertices = []
    faces = []
    try:
        with open(obj_filepath, 'r') as f:
            for line in f:
                if line.startswith('v '):
                    parts = line.strip().split()
                    if len(parts) >= 4:
                        try:
                            vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
                        except ValueError:
                            print(f"警告: 无法解析顶点行: {line.strip()}")
                            continue
                elif line.startswith('f '):
                    parts = line.strip().split()
                    face_vertex_indices = []
                    for part in parts[1:]:
                        # OBJ面定义可以是 v, v/vt, v/vt/vn, or v//vn
                        # 我们只需要顶点索引 v
                        v_index_str = part.split('/')[0]
                        try:
                            # OBJ索引是1基的，转换为0基
                            face_vertex_indices.append(int(v_index_str) - 1)
                        except ValueError:
                            print(f"警告: 无法解析面定义中的顶点索引: {part} in line {line.strip()}")
                            face_vertex_indices = [] # 无效面，跳过
                            break
                    
                    if not face_vertex_indices:
                        continue

                    # 将多边形面转换为三角形面（扇形三角剖分）
                    if len(face_vertex_indices) >= 3:
                        # 第一个顶点作为扇形中心
                        v0 = face_vertex_indices[0]
                        for i in range(1, len(face_vertex_indices) - 1):
                            v1 = face_vertex_indices[i]
                            v2 = face_vertex_indices[i+1]
                            faces.append([v0, v1, v2])
                    else:
                        print(f"警告: 面定义中的顶点数少于3: {line.strip()}")

    except FileNotFoundError:
        print(f"错误: 未找到OBJ文件 '{obj_filepath}'")
        return None, None
    except Exception as e:
        print(f"读取OBJ文件 '{obj_filepath}' 时发生错误: {e}")
        return None, None
    
    if not vertices:
        print(f"警告: 未在OBJ文件 '{obj_filepath}' 中找到有效的顶点数据。")
        return None, None
    if not faces:
        print(f"警告: 未在OBJ文件 '{obj_filepath}' 中找到有效的面数据。")
        return None, None
        
    return np.array(vertices, dtype=np.float32), np.array(faces, dtype=np.int32)

def parse_stl_to_mesh_data(stl_filepath):
    """
    从STL文件中解析顶点和面数据
    
    参数:
        stl_filepath (str): STL文件路径
    
    返回:
        tuple: (vertices, faces)，其中:
            - vertices: numpy数组，形状为(V, 3)，表示顶点坐标
            - faces: numpy数组，形状为(F, 3)，表示三角面片顶点索引
    """
    try:
        mesh = stl_mesh.Mesh.from_file(stl_filepath)
    except FileNotFoundError:
        print(f"错误: 未找到STL文件 '{stl_filepath}'")
        return None, None
    except Exception as e:
        print(f"读取STL文件 '{stl_filepath}' 时发生错误: {e}")
        return None, None

    if mesh.vectors.shape[0] == 0:
        print(f"警告: STL文件 '{stl_filepath}' 不包含任何三角面片。")
        return None, None

    # mesh.vectors 是一个 (n_faces, 3, 3) 的数组，包含每个三角面片的3个顶点坐标
    # 我们需要将其转换为唯一的顶点列表和面索引列表
    
    # 获取所有顶点，然后找出唯一的顶点
    all_vertices_flat = mesh.vectors.reshape(-1, 3)
    unique_vertices, inverse_indices = np.unique(all_vertices_flat, axis=0, return_inverse=True)
    
    # inverse_indices 现在可以用来构建面索引，每3个组成一个面
    faces = inverse_indices.reshape(-1, 3)
    
    if unique_vertices.shape[0] == 0:
        print(f"警告: 未能从STL文件 '{stl_filepath}' 中提取有效顶点。")
        return None, None
        
    return np.array(unique_vertices, dtype=np.float32), np.array(faces, dtype=np.int32)

def parse_off_to_mesh_data(off_filepath):
    """
    从OFF文件中解析顶点和面数据
    
    参数:
        off_filepath (str): OFF文件路径
    
    返回:
        tuple: (vertices, faces)，其中:
            - vertices: numpy数组，形状为(V, 3)，表示顶点坐标
            - faces: numpy数组，形状为(F, 3)，表示三角面片顶点索引
    """
    vertices = []
    faces = []
    try:
        with open(off_filepath, 'r') as f:
            header = f.readline().strip()
            if header != 'OFF':
                print(f"错误: OFF 文件 {off_filepath} 缺少OFF头。")
                return None, None
            counts = f.readline().strip()
            while counts.startswith('#') or counts == '':
                counts = f.readline().strip()
            parts = counts.split()
            if len(parts) < 2:
                print(f"错误: OFF 文件 {off_filepath} 头部格式不正确。")
                return None, None
            num_vertices = int(parts[0])
            num_faces = int(parts[1])
            # 读取顶点
            vertex_lines = []
            while len(vertex_lines) < num_vertices:
                line = f.readline()
                if not line:
                    break
                line = line.strip()
                if line == '' or line.startswith('#'):
                    continue
                vertex_lines.append(line)
            if len(vertex_lines) != num_vertices:
                print(f"错误: OFF 文件 {off_filepath} 顶点数与头部声明不符。")
                return None, None
            vertices = np.array([[float(x) for x in l.split()[:3]] for l in vertex_lines], dtype=np.float32)
            # 读取面
            face_lines = []
            while len(face_lines) < num_faces:
                line = f.readline()
                if not line:
                    break
                line = line.strip()
                if line == '' or line.startswith('#'):
                    continue
                face_lines.append(line)
            for l in face_lines:
                parts = l.split()
                if len(parts) < 4:
                    continue
                n = int(parts[0])
                if n < 3 or len(parts) < n + 1:
                    continue
                indices = [int(x) for x in parts[1:n+1]]
                # 多边形面转三角形面
                v0 = indices[0]
                for i in range(1, n-1):
                    v1 = indices[i]
                    v2 = indices[i+1]
                    faces.append([v0, v1, v2])
        if not vertices.any() or not faces:
            print(f"警告: 未在OFF文件 '{off_filepath}' 中找到有效的顶点或面数据。")
            return None, None
        return np.array(vertices, dtype=np.float32), np.array(faces, dtype=np.int32)
    except FileNotFoundError:
        print(f"错误: 未找到OFF文件 '{off_filepath}'")
        return None, None
    except Exception as e:
        print(f"读取OFF文件 '{off_filepath}' 时发生错误: {e}")
        return None, None

def sample_points_from_surface(vertices, faces, num_samples):
    """
    从网格表面随机采样点
    
    参数:
        vertices (numpy.ndarray): 顶点坐标，形状为(V, 3)
        faces (numpy.ndarray): 三角面片顶点索引，形状为(F, 3)
        num_samples (int): 采样点数
    
    返回:
        numpy.ndarray: 采样点坐标，形状为(num_samples, 3)
    """
    if vertices is None or faces is None or vertices.shape[0] == 0 or faces.shape[0] == 0:
        print("错误: 顶点或面数据为空，无法采样。")
        return None

    # 计算每个三角形的面积
    triangle_areas = np.zeros(faces.shape[0])
    for i, face in enumerate(faces):
        v0, v1, v2 = vertices[face[0]], vertices[face[1]], vertices[face[2]]
        # 使用叉积计算面积
        triangle_areas[i] = 0.5 * np.linalg.norm(np.cross(v1 - v0, v2 - v0))
    
    # 处理面积为0的退化三角形
    valid_areas_mask = triangle_areas > 1e-9
    if not np.any(valid_areas_mask):
        print("警告: 所有三角面片的面积都接近于零，无法进行基于面积的采样。将尝试随机选择面。")
        if faces.shape[0] > 0:
            probabilities = np.ones(faces.shape[0]) / faces.shape[0]
        else:
            print("错误: 没有有效的面可以采样。")
            return None
    else:
        valid_face_indices = np.arange(faces.shape[0])[valid_areas_mask]
        triangle_areas_filtered = triangle_areas[valid_areas_mask]
        probabilities = triangle_areas_filtered / np.sum(triangle_areas_filtered)
    
    # 根据面积选择三角面片
    valid_face_indices = np.arange(faces.shape[0])[valid_areas_mask]
    if len(valid_face_indices) == 0:
        print("错误: 没有有效面积的面可以采样。")
        return None

    chosen_triangle_indices_in_filtered = np.random.choice(
        len(valid_face_indices), 
        size=num_samples, 
        p=probabilities
    )
    chosen_triangle_indices = valid_face_indices[chosen_triangle_indices_in_filtered]

    # 在选定的三角形内采样点
    sampled_points = np.zeros((num_samples, 3))
    for i, tri_idx in enumerate(chosen_triangle_indices):
        v0, v1, v2 = vertices[faces[tri_idx][0]], vertices[faces[tri_idx][1]], vertices[faces[tri_idx][2]]
        # 在三角形内部使用重心坐标随机采样点
        r1 = np.random.rand()
        r2 = np.random.rand()
        # 确保点在三角形内
        if r1 + r2 > 1:
            r1 = 1 - r1
            r2 = 1 - r2
        # 使用重心坐标计算点
        u = r1
        v = r2
        w = 1 - u - v
        sampled_points[i] = w * v0 + u * v1 + v * v2
        
    return sampled_points

def main():
    parser = argparse.ArgumentParser(description="从OBJ或STL文件表面采样点云")
    parser.add_argument("input_file", help="输入的 .obj 或 .stl 文件路径")
    parser.add_argument("--num_points", type=int, default=500000, help="采样点数 (默认: 500000)")
    parser.add_argument("--output_file", help="输出文件路径，默认为在输入文件名后添加'_sampled'")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    
    args = parser.parse_args()
    
    # 设置随机种子
    np.random.seed(args.seed)
    
    # 检查输入文件
    input_filepath = args.input_file
    if not os.path.exists(input_filepath):
        print(f"错误: 输入文件 '{input_filepath}' 不存在。")
        return 1
    
    # 确定文件类型
    filename, file_extension = os.path.splitext(input_filepath)
    file_extension = file_extension.lower()
    
    # 解析网格数据
    print(f"正在处理文件: {input_filepath}")
    vertices, faces = None, None
    
    if file_extension == '.obj':
        vertices, faces = parse_obj_to_mesh_data(input_filepath)
        source_suffix = "_from_obj"
    elif file_extension == '.stl':
        vertices, faces = parse_stl_to_mesh_data(input_filepath)
        source_suffix = "_from_stl"
    elif file_extension == '.off':
        vertices, faces = parse_off_to_mesh_data(input_filepath)
        source_suffix = "_from_off"
    else:
        print(f"错误: 不支持的文件类型 '{file_extension}'。仅支持 .obj、.stl 和 .off 文件。")
        return 1
    
    if vertices is None or faces is None:
        print(f"无法从文件 '{input_filepath}' 解析网格数据。")
        return 1
    
    print(f"从文件中成功提取 {vertices.shape[0]} 个唯一顶点和 {faces.shape[0]} 个三角面片。")
    
    # 采样点云
    print(f"正在从模型表面采样点云，目标点数: {args.num_points}...")
    sampled_points = sample_points_from_surface(vertices, faces, args.num_points)
    
    if sampled_points is None:
        print("点云采样失败。")
        return 1
    
    # 准备输出文件路径
    if args.output_file:
        output_file = args.output_file
    else:
        output_file = f"{filename}_sampled{source_suffix}.ply"
    
    # 保存结果
    success = save_points_to_ply(sampled_points, None, output_file)
    
    if success:
        print(f"成功采样 {sampled_points.shape[0]} 个点，并保存到: {output_file}")
        return 0
    else:
        print(f"未能将采样点云保存到文件: {output_file}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 