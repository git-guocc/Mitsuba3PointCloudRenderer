#!/usr/bin/env python
"""
Mitsuba2 点云渲染器 - 批量渲染工具

批量渲染多个点云文件，可指定目录结构和渲染参数。
"""

import os
import sys
import argparse
import glob
import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mitsuba_pcr.render import batch_render

def main():
    parser = argparse.ArgumentParser(description="批量渲染点云文件")
    
    # 输入/输出参数
    parser.add_argument("--base_dir", required=True, help="基础目录路径")
    parser.add_argument("--methods_dirs", nargs='+', help="方法子目录列表，相对于base_dir")
    parser.add_argument("--target_cloud", help="要渲染的点云文件名 (如 'cloud.ply')")
    parser.add_argument("--pattern", default="*.ply", help="文件匹配模式 (默认: '*.ply')")
    parser.add_argument("--output_dir", help="输出目录，默认为base_dir下的'temp_renders'")
    
    # 渲染参数
    parser.add_argument("--integrator", choices=["path", "direct"], default="direct", 
                        help="Mitsuba积分器类型: path (完整光照和阴影), direct (简化光照)")
    parser.add_argument("--samples", type=int, default=256, help="每像素采样数")
    parser.add_argument("--num_points", type=int, default=50000, help="渲染点数")
    parser.add_argument("--point_radius", type=float, default=0.006, help="点半径")
    
    # 颜色参数
    parser.add_argument("--color_mode", choices=["original", "position", "height", "fixed"], default="original", 
                        help="颜色模式")
    
    # 相机参数
    parser.add_argument("--camera_params", help="相机参数: 'origin_x,origin_y,origin_z target_x,target_y,target_z up_x,up_y,up_z'")
    
    # 其他参数
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    parser.add_argument("--cleanup", action="store_true", help="清理中间文件")
    parser.add_argument("--mitsuba_path", help="Mitsuba可执行文件路径")
    
    args = parser.parse_args()
    
    # 准备输出目录
    base_dir = args.base_dir
    output_dir = args.output_dir
    if not output_dir:
        output_dir = os.path.join(base_dir, "temp_renders")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取要渲染的文件列表
    input_files = []
    
    if args.methods_dirs and args.target_cloud:
        # 如果指定了方法目录和目标点云，则渲染每个方法目录下的目标点云
        for method_dir in args.methods_dirs:
            method_path = os.path.join(base_dir, method_dir)
            if not os.path.exists(method_path):
                print(f"警告: 方法目录 {method_path} 不存在，跳过")
                continue
                
            cloud_path = os.path.join(method_path, args.target_cloud)
            if os.path.exists(cloud_path):
                input_files.append(cloud_path)
            else:
                print(f"警告: 在 {method_path} 中未找到 {args.target_cloud}")
    else:
        # 否则，使用pattern匹配base_dir下的所有文件
        pattern = os.path.join(base_dir, "**", args.pattern)
        input_files = glob.glob(pattern, recursive=True)
    
    if not input_files:
        print(f"错误: 未找到匹配的文件")
        return 1
    
    print(f"找到 {len(input_files)} 个文件进行批量渲染。")
    
    # 准备渲染配置
    config = {
        'integrator': args.integrator,
        'samples': args.samples,
        'num_points': args.num_points,
        'point_radius': args.point_radius,
        'color_mode': args.color_mode,
        'camera_params': args.camera_params,
        'seed': args.seed,
        'cleanup': args.cleanup,
        'mitsuba_path': args.mitsuba_path,
        'output_format': 'png',
    }
    
    # 执行批量渲染
    success_count, total_count = batch_render(input_files, output_dir, config)
    
    print(f"\n所有渲染完成，结果保存在: {output_dir}")
    print(f"成功: {success_count}/{total_count}")
    
    return 0 if success_count == total_count else 1

if __name__ == "__main__":
    sys.exit(main()) 